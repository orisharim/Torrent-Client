import asyncio
from typing import Optional, Tuple
import time
from peer_state import PeerState
import peer_protocol_encoder as protocol_encoder
from torrent_storage import TorrentStorage

class PeerConnection:
    DEFAULT_BLOCK_LENGTH = 16 * 1024
    CONNECTION_TIMEOUT = 10.0
    HEARTBEAT_INTERVAL = 60.0
    DEAD_CONNECTION_TIMEOUT = 120.0
    UPLOAD_TIMEOUT = 30.0
    
    MESSAGE_CHOKE = 0
    MESSAGE_UNCHOKE = 1
    MESSAGE_INTERESTED = 2
    MESSAGE_NOT_INTERESTED = 3
    MESSAGE_HAVE = 4
    MESSAGE_BITFIELD = 5
    MESSAGE_REQUEST = 6
    MESSAGE_PIECE = 7
    MESSAGE_CANCEL = 8
    MAX_IN_FLIGHT_BLOCKS_PER_PIECE = 6
    MAX_BLOCK_RETRIES = 3
    BLOCK_DOWNLOAD_TIMEOUT = 10.0

    def __init__(self, host: str, port: int, info_hash: bytes, peer_id: bytes, storage: TorrentStorage) -> None:
        self._host = host
        self._port = port
        self._info_hash = info_hash
        self._peer_id = peer_id
        self._storage = storage
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._state = PeerState()
        self._last_message_receive_time: Optional[float] = None
        self._last_message_send_time: Optional[float] = None

        self._message_loop_task: Optional[asyncio.Task] = None
        self._upload_tasks: dict[tuple[int,int], (asyncio.Task, float)] = {} # (piece_index, begin), (task, timestamp)
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._write_lock = asyncio.Lock()
        self._upload_tasks_lock = asyncio.Lock()

    async def connect(self) -> None:
        if not await self.is_connected():
            self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(self._host, self._port), timeout=self.CONNECTION_TIMEOUT)
        
    async def disconnect(self) -> None:
        await self.stop_message_loop()
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def start_message_loop(self) -> None:
        await self.connect()
        if self._message_loop_task is None or self._message_loop_task.done():
            self._message_loop_task = asyncio.create_task(self._message_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def stop_message_loop(self) -> None:
        async with self._upload_tasks_lock:
            for task, timestamp in self._upload_tasks.values():
                task.cancel()
            self._upload_tasks.clear()

        if self._message_loop_task and not self._message_loop_task.done():
            self._message_loop_task.cancel()
        self._message_loop_task = None

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = None
    

    async def _message_loop(self) -> None:
        try:
            while True:
                await self._read_message()
        except Exception:
            raise Exception("message loop terminated unexpectedly")

        finally:
            await self.disconnect()

    async def _read_message(self) -> None:
        length_prefix = await self._read_exactly(4)
        self._last_message_receive_time = time.monotonic()
        message_length = protocol_encoder.unpack_message_length_prefix(length_prefix)

        if message_length == 0:
            return  # keepalive message
        message = await self._read_exactly(message_length)
        message_id, payload = message[0], message[1:]

        if message_id == self.MESSAGE_CHOKE:
            await self._on_choke(payload)
        elif message_id == self.MESSAGE_UNCHOKE:
            await self._on_unchoke(payload)
        elif message_id == self.MESSAGE_INTERESTED:
            await self._on_interested(payload)
        elif message_id == self.MESSAGE_NOT_INTERESTED:
            await self._on_not_interested(payload)
        elif message_id == self.MESSAGE_HAVE:
            await self._on_have(payload)
        elif message_id == self.MESSAGE_BITFIELD:
            await self._on_bitfield(payload)
        elif message_id == self.MESSAGE_REQUEST:
            await self._on_request(payload)
        elif message_id == self.MESSAGE_PIECE:
            await self._on_piece(payload)
        elif message_id == self.MESSAGE_CANCEL:
            await self._on_cancel(payload)

    async def _on_choke(self, payload: bytes) -> None:
        self._state.set_peer_choking(True)
    
    async def _on_unchoke(self, payload: bytes) -> None:
        self._state.set_peer_choking(False)

    async def _on_interested(self, payload: bytes) -> None:
        self._state.set_peer_interested(True)

    async def _on_not_interested(self, payload: bytes) -> None:
        self._state.set_peer_interested(False)

    async def _on_have(self, payload: bytes) -> None:
        piece_index = protocol_encoder.unpack_have_payload(payload)
        self._state.set_piece_in_bitfield(piece_index)

    async def _on_bitfield(self, payload: bytes) -> None:
        self._state.update_bitfield(payload)

    async def _on_request(self, payload: bytes) -> None:
        if self._state.am_choking:
            return
        piece_index, begin, length = protocol_encoder.unpack_request_payload(payload, "piece")
        upload_task = asyncio.create_task(self._send_piece(piece_index, begin, length))

        async with self._upload_tasks_lock:
          self._upload_tasks[(piece_index, begin)] = (upload_task, time.monotonic())

    async def _send_piece(self, piece_index: int, begin: int, length: int) -> None:
        if piece_index < 0 or piece_index >= self._storage.total_piece_count:
            return
        if begin < 0 or length <= 0:
            return
        
        piece_length = self._storage.get_piece_length(piece_index)
        if begin >= piece_length:
            return
        
        read_length = min(length, piece_length - begin)
        data = self._storage.read_piece_bytes(piece_index, begin, read_length)
        if data is None:
            return
        payload = protocol_encoder.pack_piece_payload(piece_index, begin, data)
        try:
            await self.send_message(self.MESSAGE_PIECE, payload)
            async with self._upload_tasks_lock:
                self._upload_tasks.pop((piece_index, begin), None)
        except Exception:
            raise Exception(f"Failed to send piece {piece_index} at offset {begin} to peer")

    async def _on_piece(self, payload: bytes) -> None:
        piece_index, begin, block_data = protocol_encoder.unpack_piece_payload(payload)
        await self._storage.add_piece(piece_index, begin, block_data)

    async def _on_cancel(self, payload: bytes) -> None:
        piece_index, begin, length = protocol_encoder.unpack_request_payload(payload, "cancel")
        key = (piece_index, begin)
        async with self._upload_tasks_lock:
            task = self._upload_tasks.pop(key, None)
            if task is not None:
                task.cancel()

    async def _read_exactly(self, size: int) -> bytes:
            if self._reader is None:
                raise ConnectionError("not connected to peer")
            return await asyncio.wait_for(self._reader.readexactly(size), timeout=self.CONNECTION_TIMEOUT)
    
    async def _drain(self) -> None:
        if self._writer is None or self._writer.is_closing():
            raise ConnectionError("not connected to peer or connection is closing")
        await asyncio.wait_for(self._writer.drain(), timeout=self.CONNECTION_TIMEOUT)

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

            async with self._upload_tasks_lock:
                for key, (task, timestamp) in list(self._upload_tasks.items()):
                    if (time.monotonic() - timestamp) > self.UPLOAD_TIMEOUT:
                        task.cancel()
                        self._upload_tasks.pop(key, None)

            if self._last_message_receive_time is not None and (time.monotonic() - self._last_message_receive_time) > self.DEAD_CONNECTION_TIMEOUT:
                await self.disconnect()
                break

            if self._last_message_send_time is not None and (time.monotonic() - self._last_message_send_time) > self.HEARTBEAT_INTERVAL:
                await self.send_message(None)
                
            

    async def send_handshake(self):
        await self.connect()
        handshake = protocol_encoder.pack_handshake(self._info_hash, self._peer_id)
                
        async with self._write_lock:
            if self._writer is None or self._writer.is_closing():
                raise ConnectionError("connection was closed during write")
            self._writer.write(handshake)
            await self._drain()
            self._last_message_send_time = time.monotonic()
        
        response = await self._read_exactly(68)

        self._last_message_receive_time = time.monotonic()
        _, remote_peer_id = protocol_encoder.unpack_handshake(response, expected_info_hash=self._info_hash)
        self._state.remote_peer_id = remote_peer_id

    async def send_message(self, message_id: Optional[int], payload: bytes = b"") -> None:
        await self.connect()
        if self._writer is None or self._writer.is_closing():
            raise ConnectionError("not connected to peer or connection is closing")
        if message_id is None:
            packet = protocol_encoder.pack_keepalive()
        else:
            packet = protocol_encoder.pack_message(message_id, payload)
    
        async with self._write_lock:
            if self._writer is None or self._writer.is_closing():
                raise ConnectionError("connection was closed during write")
            self._writer.write(packet)
            await self._drain()
            self._last_message_send_time = time.monotonic()
    
    async def send_interested(self) -> None:
        self._state.set_am_interested(True)
        await self.send_message(self.MESSAGE_INTERESTED)
    
    async def send_not_interested(self) -> None:
        self._state.set_am_interested(False)
        await self.send_message(self.MESSAGE_NOT_INTERESTED)
    
    async def send_choke(self) -> None:
        self._state.set_am_choking(True)
        await self.send_message(self.MESSAGE_CHOKE)
    
    async def send_unchoke(self) -> None:
        self._state.set_am_choking(False)
        await self.send_message(self.MESSAGE_UNCHOKE)
    
    async def send_bitfield(self, bitfield: bytes) -> None:
        await self.send_message(self.MESSAGE_BITFIELD, bitfield)
    
    async def send_have(self, piece_index: int) -> None:
        payload = protocol_encoder.pack_have_payload(piece_index)
        await self.send_message(self.MESSAGE_HAVE, payload)

    async def send_block_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        await self.send_message(self.MESSAGE_REQUEST, payload)
    
    async def send_cancel_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        await self.send_message(self.MESSAGE_CANCEL, payload) 

    async def send_piece_request(self, piece_index: int) -> None:
        piece_length = self._storage.get_piece_length(piece_index)
        
        block_queue = asyncio.Queue()
        for begin in range(0, piece_length, self.DEFAULT_BLOCK_LENGTH):
            length = min(self.DEFAULT_BLOCK_LENGTH, piece_length - begin)
            await block_queue.put((begin, length))

        async def worker():
            while not block_queue.empty():
                await block_queue.join()
                try:
                    begin, length = await block_queue.get()
                except asyncio.QueueEmpty:
                    break
                await self.send_block_request(piece_index, begin, length)
                block_queue.task_done()
                

        async with asyncio.TaskGroup() as tg:
            for _ in range(min(self.MAX_IN_FLIGHT_BLOCKS_PER_PIECE, block_queue.qsize())):
                tg.create_task(worker())

    async def is_choked(self) -> bool:
        return self._state.is_peer_choking()
         
    async def is_interested(self) -> bool:
        return self._state.is_am_interested()
     
    async def is_connected(self) -> bool:
        return self._reader is not None and self._writer is not None   

    async def get_bitfield(self) -> Optional[bytes]:
        return self._state.get_bitfield()

    
            
    