import asyncio
from typing import Optional, Tuple
import time
from TorrentSession.peers.peer_state import PeerState
import TorrentSession.peers.peer_protocol_encoder as protocol_encoder
from TorrentSession.piece import Piece
from TorrentSession.torrent_storage import TorrentStorage
from TorrentSession.session_logger import SessionLogger

class PeerConnection:
    CONNECTION_TIMEOUT = 20.0
    HEARTBEAT_INTERVAL = 60.0
    CLOSE_CONNECTION_TIMEOUT = 120.0
    UPLOAD_TIMEOUT = 30.0
    REQUEST_TIMEOUT = 30.0
    
    MESSAGE_CHOKE = 0
    MESSAGE_UNCHOKE = 1
    MESSAGE_INTERESTED = 2
    MESSAGE_NOT_INTERESTED = 3
    MESSAGE_HAVE = 4
    MESSAGE_BITFIELD = 5
    MESSAGE_REQUEST = 6
    MESSAGE_PIECE = 7
    MESSAGE_CANCEL = 8

    def __init__(self, info_hash: bytes, peer_id: bytes, storage: TorrentStorage, logger: SessionLogger | None = None) -> None:
        self._info_hash = info_hash
        self._peer_id = peer_id
        self._storage = storage
        self._logger = logger
        self._closing = False
        self._handshake_done = False

        self._receive_message_loop_task: Optional[asyncio.Task] = None
        self._upload_tasks: dict[tuple[int,int], tuple[asyncio.Task, float]] = {} # (piece_index, begin), (task, timestamp)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._requested_pieces: dict[tuple[int, int], tuple[Piece, float]] = {} # (piece_index, begin), (piece, timestamp)

        self._write_lock = asyncio.Lock()
        self._upload_tasks_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self._disconnect_lock = asyncio.Lock()
        self._requested_pieces_lock = asyncio.Lock()

        self._state = PeerState()
        self._state.update_bitfield(protocol_encoder.generate_empty_bitfield(total_piece_count = self._storage.get_total_piece_count()))

    @classmethod
    def from_address(cls, host: str, port: int, info_hash: bytes, peer_id: bytes, storage: TorrentStorage, logger: SessionLogger | None = None) -> 'PeerConnection':
        peer = cls(info_hash, peer_id, storage, logger)
        peer._host = host
        peer._port = port
        peer._reader = None
        peer._writer = None
        peer._last_message_receive_time = None
        peer._last_message_send_time = None
        return peer

    @classmethod
    def from_connection(cls, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, info_hash: bytes, peer_id: bytes, storage: TorrentStorage, logger: SessionLogger | None = None) -> 'PeerConnection':
        peer = cls(info_hash, peer_id, storage, logger)
        peer._reader = reader
        peer._writer = writer
        peer._host = None
        peer._port = None
        try:
            peername = writer.get_extra_info('peername') if writer else None
            if peername is not None:
                peer._host, peer._port = peername[0], peername[1]
        except Exception:
            pass
        peer._last_message_receive_time = time.monotonic()
        peer._last_message_send_time = time.monotonic()
        return peer

    async def accept_handshake(self, remote_peer_id: bytes) -> None:
        self._state.set_remote_peer_id(remote_peer_id)
        self._handshake_done = True

    async def connect(self) -> bool:
        async with self._connect_lock:
            if self._closing:
                return False

            if self._is_connected():
                return True

            try:
                await self._ensure_stream()
                await self._perform_handshake()
                return True
            except Exception as exc:
                await self.disconnect()
                if self._logger:
                    self._logger.log_by_file("peer_connection", f"Peer connection failed for {self._host}:{self._port}: {type(exc).__name__}: {exc}")
                return False

    def _is_connected(self) -> bool:
        return (
            self._reader is not None
            and self._writer is not None
            and not self._writer.is_closing()
            and self._handshake_done
        )

    async def _ensure_stream(self) -> None:
        if self._writer is not None and self._writer.is_closing():
            await self.disconnect()

        if self._reader is not None and self._writer is not None:
            return
        if self._host is None or self._port is None:
            raise ConnectionError("peer address is not available")

        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port),
            timeout=self.CONNECTION_TIMEOUT,
        )
        self._last_message_receive_time = time.monotonic()
        self._last_message_send_time = time.monotonic()
        self._handshake_done = False

    async def _perform_handshake(self) -> None:
        if self._handshake_done:
            return

        handshake = protocol_encoder.pack_handshake(self._info_hash, self._peer_id)
        self._writer.write(handshake)
        await asyncio.wait_for(self._writer.drain(), timeout=self.CONNECTION_TIMEOUT)

        response = await asyncio.wait_for(
            self._reader.readexactly(68), timeout=self.CONNECTION_TIMEOUT
        )
        _, remote_peer_id = protocol_encoder.unpack_handshake(
            response, expected_info_hash=self._info_hash
        )
        self._state.set_remote_peer_id(remote_peer_id)
        self._handshake_done = True

    async def disconnect(self) -> None:
        async with self._disconnect_lock:
            if self._closing:
                return

            self._closing = True
            try:
                await self._cancel_background_tasks()
                writer = self._writer
                self._writer = None
                self._reader = None
                self._handshake_done = False

                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
            finally:
                self._closing = False

    async def close(self) -> None:
        await self.disconnect()

    async def start_message_loop(self) -> bool:
        if self._closing:
            return False

        if not await self.connect():
            return False

        async with self._connect_lock:
            if self._receive_message_loop_task is not None and not self._receive_message_loop_task.done():
                return True

            try:
                #send bitfield
                bitfield = self._storage.get_bitfield()
                bitfield_packet = protocol_encoder.pack_message(self.MESSAGE_BITFIELD, bitfield)
                self._writer.write(bitfield_packet)
                await asyncio.wait_for(self._writer.drain(), timeout=self.CONNECTION_TIMEOUT)

                #start message loop and heartbeat tasks
                self._receive_message_loop_task = asyncio.create_task(self._message_loop())
                self._heartbeat_task = asyncio.create_task(self._heartbeat())

                await self.update_interest()
                return True
            except Exception:
                await self.disconnect()
                return False

    async def stop_message_loop(self) -> None:
        await self.disconnect()

    async def _cancel_background_tasks(self) -> None:
        tasks_to_cancel = []
        current_task = asyncio.current_task()

        if self._receive_message_loop_task and not self._receive_message_loop_task.done() and self._receive_message_loop_task is not current_task:
            tasks_to_cancel.append(self._receive_message_loop_task)
        if self._heartbeat_task and not self._heartbeat_task.done() and self._heartbeat_task is not current_task:
            tasks_to_cancel.append(self._heartbeat_task)
        async with self._upload_tasks_lock:
            for task, timestamp in self._upload_tasks.values():
                if task is not current_task and not task.done():
                    tasks_to_cancel.append(task)
            self._upload_tasks.clear()

        for task in tasks_to_cancel:
            task.cancel()
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        async with self._requested_pieces_lock:
            self._requested_pieces.clear()

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
            if self._logger:
                self._logger.log_by_file("peer_connection", f"Peer message loop failed for {self._host}:{self._port}: {exc}")

    async def _read_message(self) -> None:
        length_prefix = await self._read_exactly(4, timeout=self.CLOSE_CONNECTION_TIMEOUT)
        self._last_message_receive_time = time.monotonic()
        message_length = protocol_encoder.unpack_message_length_prefix(length_prefix)

        if message_length == 0:
            return  # keepalive message
        message = await self._read_exactly(message_length, timeout=self.CONNECTION_TIMEOUT)
        message_id, payload = message[0], message[1:]

        if self._logger:
            self._logger.log_incoming_message(
                f"from {self._host}:{self._port} - ID: {message_id}, Payload Length: {len(payload)}"
            )

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
        if self._logger:
            self._logger.log_peer_state_change("choked us", f"{self._host}:{self._port}")
    
    async def _on_unchoke(self, payload: bytes) -> None:
        self._state.set_peer_choking(False)
        if self._logger:
            self._logger.log_peer_state_change("unchoked us", f"{self._host}:{self._port}")

    async def _on_interested(self, payload: bytes) -> None:
        self._state.set_peer_interested(True)
        if self._state.get_am_seeding():
            await self.send_unchoke()

    async def _on_not_interested(self, payload: bytes) -> None:
        self._state.set_peer_interested(False)
        if self._state.get_am_seeding():
            await self.send_choke()

    async def _on_have(self, payload: bytes) -> None:
        piece_index = protocol_encoder.unpack_have_payload(payload)
        self._state.set_piece_in_bitfield(piece_index)
        await self.update_interest()

    async def _on_bitfield(self, payload: bytes) -> None:
        self._state.update_bitfield(payload)
        await self.update_interest()

    async def _on_request(self, payload: bytes) -> None:
        if (self._state.get_am_choking() or not self._state.get_am_seeding() or not self._state.is_peer_interested()):
            return
        piece_index, begin, length = protocol_encoder.unpack_request_payload(payload, "piece")
        if self._logger:
            self._logger.log_peer_piece_request(piece_index)

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
            if not await self.send_message(self.MESSAGE_PIECE, payload):
                raise ConnectionError("peer rejected the piece message")
            await self._storage.record_uploaded_piece(piece_index, len(data))
            if self._logger:
                self._logger.log_uploaded_piece(
                    piece_index,
                    f"{self._host}:{self._port}",
                )
            
        except Exception as exc:
            if self._logger:
                self._logger.log_upload_error(piece_index, begin, str(exc))
            raise ConnectionError(
                f"Failed to send piece {piece_index} at offset {begin} to peer"
            ) from exc
        finally:
            async with self._upload_tasks_lock:
                self._upload_tasks.pop((piece_index, begin), None)

    async def start_seeding(self):
        self._state.set_am_seeding(True)
        return await self.send_unchoke()

    async def stop_seeding(self):
        self._state.set_am_seeding(False)
        return await self.send_choke()

    async def _on_piece(self, payload: bytes) -> None:
        piece_index, begin, block_data = protocol_encoder.unpack_piece_payload(payload)

        if piece_index < 0 or piece_index >= self._storage._total_piece_count:
            return

        if await self._storage.is_piece_downloaded(piece_index):
            async with self._requested_pieces_lock:
                self._requested_pieces.pop((piece_index, begin), None)
            return

        async with self._requested_pieces_lock:
            request_info = self._requested_pieces.get((piece_index, begin))
            if request_info is None:
                if self._logger:
                    self._logger.log_ignored_block(piece_index, begin, f"{self._host}:{self._port}")
                return
        
        if begin < 0 or len(block_data) <= 0 or begin >= self._storage.get_piece_length(piece_index):
            async with self._requested_pieces_lock:
                self._requested_pieces.pop((piece_index, begin), None)
            return
        
        piece = request_info[0]
        if not piece.add_block(begin, block_data):
            async with self._requested_pieces_lock:
                self._requested_pieces.pop((piece_index, begin), None)
            return

        if self._logger:
            self._logger.log_received_block(piece_index, begin, len(block_data), f"{piece.get_received_byte_count()}/{piece.length}", f"{self._host}:{self._port}" )

        async with self._requested_pieces_lock:
            self._requested_pieces.pop((piece_index, begin), None)

        
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

            now = time.monotonic()
            async with self._requested_pieces_lock:
                expired_requests = [
                    key for key, (_, timestamp) in self._requested_pieces.items()
                    if now - timestamp > self.REQUEST_TIMEOUT
                ]
                for key in expired_requests:
                    self._requested_pieces.pop(key, None)

            if self._last_message_receive_time is not None and (time.monotonic() - self._last_message_receive_time) > self.CLOSE_CONNECTION_TIMEOUT:
                await self.disconnect()
                break

            if self._last_message_send_time is None or (time.monotonic() - self._last_message_send_time) > self.HEARTBEAT_INTERVAL:
                try:
                    await self._write_packet(protocol_encoder.pack_keepalive())
                except ConnectionError:
                    await self.disconnect()
                    break

    
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
        except (ConnectionError, asyncio.TimeoutError, ValueError):
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

    async def send_piece_request(self, piece_index: int, begin: int, length: int, piece: Piece) -> bool:
        if self._state.is_peer_choking():
            if self._logger:
                self._logger.log_block_request_failure("blocked because peer is choking", piece_index, f"{self._host}:{self._port}")
            return False
        if self._state.is_am_interested() is False:
            if not await self.send_interested():
                return False
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        async with self._requested_pieces_lock:
            self._requested_pieces[(piece_index, begin)] = (piece, time.monotonic())
        sent = await self.send_message(self.MESSAGE_REQUEST, payload)
        if not sent:
            async with self._requested_pieces_lock:
                self._requested_pieces.pop((piece_index, begin), None)
        else:
            if self._logger:
                self._logger.log_peer_piece_request(piece_index, f"{self._host}:{self._port}")
        return sent
    
    async def send_cancel_request(self, piece_index: int, begin: int, length: int) -> bool:
        async with self._requested_pieces_lock:
            self._requested_pieces.pop((piece_index, begin), None)
                
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        return await self.send_message(self.MESSAGE_CANCEL, payload) 

    async def clear_pending_request(self, piece_index: int, begin: int) -> None:
        async with self._requested_pieces_lock:
            self._requested_pieces.pop((piece_index, begin), None) 

    async def is_choked(self) -> bool:
        return self._state.is_peer_choking()
         
    async def is_interested(self) -> bool:
        return self._state.is_am_interested()
     
    async def is_connected(self) -> bool:
        return (self._reader is not None and 
                self._writer is not None and 
                not self._writer.is_closing())

    async def is_message_loop_running(self) -> bool:
        return self._receive_message_loop_task is not None and not self._receive_message_loop_task.done()

    async def get_bitfield(self) -> Optional[bytes]:
        return self._state.get_bitfield()

    def get_piece(self, piece_index: int) -> Optional[Piece]:
        for (requested_index, _), (piece, _) in self._requested_pieces.items():
            if requested_index == piece_index:
                return piece
        return None

    def get_requested_block_count(self) -> int:
        return len(self._requested_pieces)

    def get_requested_pieces(self) -> list[tuple[int, int]]:
        return list(self._requested_pieces.keys())
            
    def can_download_piece(self, piece_index: int) -> bool:
        bitfield = self._state.get_bitfield()
        if bitfield is None:
            return False
        return protocol_encoder.check_bitfield_has_piece(bitfield, piece_index) and not self._state.is_peer_choking()
          
    async def update_interest(self) -> bool:
        peer_bitfield = self._state.get_bitfield()
        if peer_bitfield is None:
            if not self._storage.is_complete():
                if not self._state.is_am_interested():
                    return await self.send_interested()
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

    