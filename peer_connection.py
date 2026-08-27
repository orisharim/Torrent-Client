import asyncio
from typing import Optional, Tuple
import time
from peer_state import PeerState
import peer_protocol_encoder as protocol_encoder
from piece import Piece
from torrent_storage import TorrentStorage

class PeerConnection:
    PRINT_INCOMING_MESSAGES = False
    PRINT_DOWNLOADED_PIECES = False

    DEFAULT_BLOCK_LENGTH = 16 * 1024
    CONNECTION_TIMEOUT = 10.0
    BITFIELD_RECEIVE_TIMEOUT = 10.0
    BITFIELD_INTERVAL = 1.0
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

        self._state.update_bitfield(protocol_encoder.generate_empty_bitfield(total_piece_count = self._storage.get_total_piece_count()))
        self._state.set_am_choking(True)
        self._state.set_am_interested(False)
        self._state.set_peer_choking(True)
        self._state.set_peer_interested(False)

    async def connect(self) -> bool:
        if self._closing:
            return False

        async with self._connect_lock:
            if self._closing:
                return False
            if (self._writer is not None and 
                self._reader is not None and 
                not self._writer.is_closing() and 
                self._receive_message_loop_task is not None and 
                not self._receive_message_loop_task.done()):
                return True

            await self.disconnect()

            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port), 
                    timeout=self.CONNECTION_TIMEOUT
                )
                self._last_message_receive_time = time.monotonic()
                self._last_message_send_time = time.monotonic()

                # Perform Handshake
                handshake = protocol_encoder.pack_handshake(self._info_hash, self._peer_id)
                self._writer.write(handshake)
                await asyncio.wait_for(self._writer.drain(), timeout=self.CONNECTION_TIMEOUT)

                response = await asyncio.wait_for(self._reader.readexactly(68), timeout=self.CONNECTION_TIMEOUT)
                remote_info_hash, remote_peer_id = protocol_encoder.unpack_handshake(response, expected_info_hash=self._info_hash)
                self._state.set_remote_peer_id(remote_peer_id)
                if remote_info_hash != self._info_hash:
                    await self.disconnect()
                    return False

                # Send Bitfield
                bitfield = self._storage.get_bitfield()
                bitfield_packet = protocol_encoder.pack_message(self.MESSAGE_BITFIELD, bitfield)
                self._writer.write(bitfield_packet)
                await asyncio.wait_for(self._writer.drain(), timeout=self.CONNECTION_TIMEOUT)

                # Start Message Loop & Heartbeat tasks
                self._receive_message_loop_task = asyncio.create_task(self._message_loop())
                self._heartbeat_task = asyncio.create_task(self._heartbeat())

                return True
            except Exception:
                await self.disconnect()
                return False

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

    async def start_message_loop(self) -> bool:
        return await self.connect()

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
        length_prefix = await self._read_exactly(4, timeout=self.DEAD_CONNECTION_TIMEOUT)
        self._last_message_receive_time = time.monotonic()
        message_length = protocol_encoder.unpack_message_length_prefix(length_prefix)

        if message_length == 0:
            return  # keepalive message
        message = await self._read_exactly(message_length, timeout=self.CONNECTION_TIMEOUT)
        message_id, payload = message[0], message[1:]

        if PeerConnection.PRINT_INCOMING_MESSAGES:
            print(f"Received message from {self._host}:{self._port} - ID: {message_id}, Payload Length: {len(payload)}")

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
        await self.update_interest()

    async def _on_bitfield(self, payload: bytes) -> None:
        self._state.update_bitfield(payload)
        await self.update_interest()

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
        if await self._storage.is_piece_downloaded(piece_index):
            return
        if begin < 0 or len(block_data) <= 0 or begin >= self._storage.get_piece_length(piece_index):
            return
        
        self._requested_pieces[piece_index].add_block(begin, block_data)

        if self._requested_pieces[piece_index].is_complete():
            piece_data = self._requested_pieces[piece_index].get_assembled_data()
            await self._storage.add_piece(piece_index, None, piece_data)
            self._requested_pieces.pop(piece_index, None)
            
            if PeerConnection.PRINT_DOWNLOADED_PIECES:
                print(f"From {int.from_bytes(self._state.peer_id)} - Piece {piece_index} completed ")
        
    async def _on_cancel(self, payload: bytes) -> None:
        piece_index, begin, length = protocol_encoder.unpack_request_payload(payload, "cancel")
        key = (piece_index, begin)
        async with self._upload_tasks_lock:
            task_info = self._upload_tasks.pop(key, None)
            if task_info is not None:
                task, _ = task_info
                task.cancel()

    async def _read_exactly(self, size: int, timeout: Optional[float] = None) -> bytes:
            if self._reader is None:
                raise ConnectionError("not connected to peer")
            if timeout is None:
                timeout = self.CONNECTION_TIMEOUT
            try:
                return await asyncio.wait_for(self._reader.readexactly(size), timeout=timeout)
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

    async def send_handshake(self) -> bool:
        if not await self.connect():
            return False
        handshake = protocol_encoder.pack_handshake(self._info_hash, self._peer_id)
                
        try:
            await self._write_packet(handshake)
            response = await self._read_exactly(68)
        except Exception:
            await self.disconnect()
            return False

        self._last_message_receive_time = time.monotonic()
        try:
            remote_info_hash, remote_peer_id = protocol_encoder.unpack_handshake(response, expected_info_hash=self._info_hash)
            self._state.set_remote_peer_id(remote_peer_id)
            if remote_info_hash != self._info_hash:
                await self.disconnect()
                return False
            return True
        except Exception:
            await self.disconnect()
            return False

    async def send_message(self, message_id: Optional[int], payload: bytes = b"") -> bool:
        if self._closing:
            return False

        if not await self.connect():
            return False
            
        if message_id is None or payload is None:
            packet = protocol_encoder.pack_keepalive()
        else:
            packet = protocol_encoder.pack_message(message_id, payload)
        try:
            await self._write_packet(packet)
            return True
        except Exception:
            return False
                
    async def send_interested(self) -> bool:
        self._state.set_am_interested(True)
        return await self.send_message(self.MESSAGE_INTERESTED)
    
    async def send_not_interested(self) -> bool:
        self._state.set_am_interested(False)
        return await self.send_message(self.MESSAGE_NOT_INTERESTED)
    
    async def send_choke(self) -> bool:
        self._state.set_am_choking(True)
        return await self.send_message(self.MESSAGE_CHOKE)
    
    async def send_unchoke(self) -> bool:
        self._state.set_am_choking(False)
        return await self.send_message(self.MESSAGE_UNCHOKE)
    
    async def send_bitfield(self, bitfield: bytes) -> bool:
        return await self.send_message(self.MESSAGE_BITFIELD, bitfield)
    
    async def send_have(self, piece_index: int) -> bool:
        payload = protocol_encoder.pack_have_payload(piece_index)
        return await self.send_message(self.MESSAGE_HAVE, payload)

    async def send_block_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> bool:
        if self._state.is_peer_choking():
            return False
        if self._state.is_am_interested() is False:
            if not await self.send_interested():
                return False
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        return await self.send_message(self.MESSAGE_REQUEST, payload)
    
    async def send_cancel_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> bool:
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        return await self.send_message(self.MESSAGE_CANCEL, payload) 

    async def send_piece_request(self, piece_index: int) -> bool:
        async with self._requested_pieces_lock:
            if piece_index in self._requested_pieces:
                return False
            piece = Piece(piece_index, self._storage.get_piece_length(piece_index))
            self._requested_pieces[piece_index] = piece

        try:
            piece_length = self._storage.get_piece_length(piece_index)
            if piece_length <= 0:
                return False

            semaphore = asyncio.Semaphore(self.MAX_IN_FLIGHT_BLOCKS_PER_PIECE)
            requests = []

            for begin in range(0, piece_length, self.DEFAULT_BLOCK_LENGTH):
                length = min(self.DEFAULT_BLOCK_LENGTH, piece_length - begin)

                async def request_block(offset: int, block_length: int) -> bool:
                    async with semaphore:
                        return await self.send_block_request(piece_index, offset, block_length)

                requests.append(request_block(begin, length))

            if requests:
                results = await asyncio.gather(*requests)
                return all(results)
            return True
        except Exception:
            async with self._requested_pieces_lock:
                self._requested_pieces.pop(piece_index, None)
            return False

    async def is_choked(self) -> bool:
        return self._state.is_peer_choking()
         
    async def is_interested(self) -> bool:
        return self._state.is_am_interested()
     
    async def is_connected(self) -> bool:
        return (self._reader is not None and 
                self._writer is not None and 
                not self._writer.is_closing() and 
                self._receive_message_loop_task is not None and 
                not self._receive_message_loop_task.done())

    async def is_message_loop_running(self) -> bool:
        return self._receive_message_loop_task is not None and not self._receive_message_loop_task.done()

    async def get_bitfield(self) -> Optional[bytes]:
        return self._state.get_bitfield()

    def get_piece(self, piece_index: int) -> Optional[Piece]:
        return self._requested_pieces.get(piece_index, None)

    def get_requested_pieces(self) -> list[int]:
        return list(self._requested_pieces.keys())
            
    def can_download_piece(self, piece_index: int) -> bool:
        bitfield = self._state.get_bitfield()
        if bitfield is None:
            return False
        return protocol_encoder.check_bitfield_has_piece(bitfield, piece_index) and not self._state.is_peer_choking()

    async def cancel_piece(self, piece_index: int) -> None:
        async with self._requested_pieces_lock:
            piece = self._requested_pieces.pop(piece_index, None)
        
        if piece is not None:
            piece_length = self._storage.get_piece_length(piece_index)
            for begin in range(0, piece_length, self.DEFAULT_BLOCK_LENGTH):
                if begin not in piece.blocks:
                    length = min(self.DEFAULT_BLOCK_LENGTH, piece_length - begin)
                    try:
                        await self.send_cancel_request(piece_index, begin, length)
                    except Exception:
                        pass

    async def update_interest(self) -> bool:
        peer_bitfield = self._state.get_bitfield()
        if peer_bitfield is None:
            return False
        
        has_interesting_pieces = False
        my_bitfield = self._storage.get_bitfield()
        for idx in range(self._storage.get_total_piece_count()):
            if protocol_encoder.check_bitfield_has_piece(peer_bitfield, idx) and not protocol_encoder.check_bitfield_has_piece(my_bitfield, idx):
                has_interesting_pieces = True
                break
        
        if has_interesting_pieces:
            if not self._state.is_am_interested():
                return await self.send_interested()
        else:
            if self._state.is_am_interested():
                return await self.send_not_interested()
        return True