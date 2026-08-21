import asyncio
from typing import Optional, Tuple
import time
from peer_state import PeerState
import peer_protocol_encoder as protocol_encoder
from piece import Piece
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
        self._closing = False

        self._receive_message_loop_task: Optional[asyncio.Task] = None
        self._upload_tasks: dict[tuple[int,int], (asyncio.Task, float)] = {} # (piece_index, begin), (task, timestamp)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._requested_pieces: dict[int, Piece] = {}

        self._write_lock = asyncio.Lock()
        self._upload_tasks_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self._disconnect_lock = asyncio.Lock()
        self._requested_pieces_lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._closing:
            raise ConnectionError("peer connection is closing")

        async with self._connect_lock:
            if self._closing:
                raise ConnectionError("peer connection is closing")
            if self._writer is not None and not self._writer.is_closing() and self._reader is not None:
                return

            self._reader = None
            self._writer = None
            self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(self._host, self._port), timeout=self.CONNECTION_TIMEOUT)
            self._last_message_receive_time = time.monotonic()
            self._last_message_send_time = time.monotonic()

    async def disconnect(self) -> None:
        if self._closing:
            return

        async with self._disconnect_lock:
            if self._closing:
                return

            self._closing = True
            try:
                await self._cancel_background_tasks()
                writer = self._writer
                self._writer = None
                self._reader = None

                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
            finally:
                self._closing = False

    async def start_message_loop(self) -> None:
        await self.stop_message_loop()
        await self.connect()

        if self._receive_message_loop_task is None or self._receive_message_loop_task.done():
            self._receive_message_loop_task = asyncio.create_task(self._message_loop())

        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def stop_message_loop(self) -> None:
        await self._cancel_background_tasks()

    async def _cancel_background_tasks(self) -> None:
        upload_tasks: list[asyncio.Task] = []
        async with self._upload_tasks_lock:
            for task, timestamp in self._upload_tasks.values():
                upload_tasks.append(task)
            self._upload_tasks.clear()

        for task in upload_tasks:
            task.cancel()
        if upload_tasks:
            await asyncio.gather(*upload_tasks, return_exceptions=True)

        tasks_to_cancel = []
        current_task = asyncio.current_task()

        if self._receive_message_loop_task and not self._receive_message_loop_task.done() and self._receive_message_loop_task is not current_task:
            tasks_to_cancel.append(self._receive_message_loop_task)
        if self._heartbeat_task and not self._heartbeat_task.done():
            tasks_to_cancel.append(self._heartbeat_task)

        for task in tasks_to_cancel:
            task.cancel()
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        self._receive_message_loop_task = None
        self._heartbeat_task = None

    async def _message_loop(self) -> None:
        try:
            while True:
                await self._read_message()
        except asyncio.CancelledError:
            raise
        except ConnectionError:
            if not self._closing:
                await self.disconnect()
            return
        except Exception as exc:
            if not self._closing:
                await self.disconnect()
            raise RuntimeError("Peer connection message loop terminated unexpectedly") from exc

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

        async with self._upload_tasks_lock:
            request_key = (piece_index, begin)
            if request_key in self._upload_tasks:
                return
            upload_task = asyncio.create_task(self._send_piece(piece_index, begin, length))
            self._upload_tasks[request_key] = (upload_task, time.monotonic())

    async def _send_piece(self, piece_index: int, begin: int, length: int) -> None:
        if piece_index < 0 or piece_index >= self._storage._total_piece_count:
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
            
        except Exception:
            raise Exception(f"Failed to send piece {piece_index} at offset {begin} to peer")
        finally:
            async with self._upload_tasks_lock:
                self._upload_tasks.pop((piece_index, begin), None)

    async def _on_piece(self, payload: bytes) -> None:
        piece_index, begin, block_data = protocol_encoder.unpack_piece_payload(payload)

        if piece_index < 0 or piece_index >= self._storage._total_piece_count:
            return
        if piece_index not in self._requested_pieces:
            return
        if self._storage.is_piece_downloaded(piece_index):
            return
        if begin < 0 or len(block_data) <= 0 or begin >= self._storage.get_piece_length(piece_index):
            return
        
        self._requested_pieces[piece_index].add_block(begin, block_data)

        if self._requested_pieces[piece_index].is_complete():
            piece_data = self._requested_pieces[piece_index].get_data()
            if piece_data is not None:
                self._storage.write_piece(piece_index, piece_data)
                self._state.set_piece_in_bitfield(piece_index)
                self._requested_pieces.pop(piece_index, None)
        
    async def _on_cancel(self, payload: bytes) -> None:
        piece_index, begin, length = protocol_encoder.unpack_request_payload(payload, "cancel")
        key = (piece_index, begin)
        async with self._upload_tasks_lock:
            task_info = self._upload_tasks.pop(key, None)
            if task_info is not None:
                task, _ = task_info
                task.cancel()

    async def _read_exactly(self, size: int) -> bytes:
            if self._reader is None:
                raise ConnectionError("not connected to peer")
            try:
                return await asyncio.wait_for(self._reader.readexactly(size), timeout=self.CONNECTION_TIMEOUT)
            except asyncio.TimeoutError as exc:
                raise ConnectionError("peer read timed out") from exc
            except asyncio.IncompleteReadError as exc:
                raise ConnectionError("peer closed the connection") from exc
            except (ConnectionResetError, BrokenPipeError, OSError) as exc:
                raise ConnectionError("connection reset by peer") from exc

    async def _write_packet(self, packet: bytes) -> None:
        async with self._write_lock:
            if self._writer is None or self._writer.is_closing():
                raise ConnectionError("not connected to peer or connection is closing")
            self._writer.write(packet)
            await self._drain()
            self._last_message_send_time = time.monotonic()
    
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

            if self._last_message_send_time is None or (time.monotonic() - self._last_message_send_time) > self.HEARTBEAT_INTERVAL:
                try:
                    await self._write_packet(protocol_encoder.pack_keepalive())
                except ConnectionError:
                    await self.disconnect()
                    break

    async def send_handshake(self):
        await self.connect()
        handshake = protocol_encoder.pack_handshake(self._info_hash, self._peer_id)
                
        await self._write_packet(handshake)
        
        response = await self._read_exactly(68)

        self._last_message_receive_time = time.monotonic()
        _, remote_peer_id = protocol_encoder.unpack_handshake(response, expected_info_hash=self._info_hash)
        self._state.remote_peer_id = remote_peer_id

    async def send_message(self, message_id: Optional[int], payload: bytes = b"") -> None:
        if self._closing:
            raise ConnectionError("peer connection is closing")

        await self.connect()
        packet = protocol_encoder.pack_message(message_id, payload) if message_id is not None else protocol_encoder.pack_keepalive()
        await self._write_packet(packet)
                
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
        async with self._requested_pieces_lock:
            if piece_index in self._requested_pieces:
                return
            piece = Piece(piece_index, self._storage.get_piece_length(piece_index))
            self._requested_pieces[piece_index] = piece

        try:
            piece_length = self._storage.get_piece_length(piece_index)
            if piece_length <= 0:
                return

            semaphore = asyncio.Semaphore(self.MAX_IN_FLIGHT_BLOCKS_PER_PIECE)
            requests = []

            for begin in range(0, piece_length, self.DEFAULT_BLOCK_LENGTH):
                length = min(self.DEFAULT_BLOCK_LENGTH, piece_length - begin)

                async def request_block(offset: int, block_length: int) -> None:
                    async with semaphore:
                        await self.send_block_request(piece_index, offset, block_length)

                requests.append(request_block(begin, length))

            if requests:
                await asyncio.gather(*requests)
        finally:
            async with self._requested_pieces_lock:
                self._requested_pieces.pop(piece_index, None)

    async def is_choked(self) -> bool:
        return self._state.is_peer_choking()
         
    async def is_interested(self) -> bool:
        return self._state.is_am_interested()
     
    async def is_connected(self) -> bool:
        writer = self._writer
        reader = self._reader
        return reader is not None and writer is not None and not writer.is_closing()

    async def get_bitfield(self) -> Optional[bytes]:
        return self._state.get_bitfield()

    def get_piece(self, piece_index: int) -> Optional[Piece]:
        return self._requested_pieces.get(piece_index, None)

    
            
    