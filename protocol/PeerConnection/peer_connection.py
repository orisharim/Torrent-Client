import asyncio
from typing import Optional, Tuple

from protocol.PeerConnection.peer_state import PeerState
from protocol.PeerConnection import peer_protocol_encoder as protocol_encoder
from protocol.piece import Piece
from protocol.torrent_storage import TorrentStorage

class PeerConnection:
    DEFAULT_BLOCK_LENGTH = 16 * 1024
    CONNECTION_TIMEOUT = 10.0
    WAIT_FOR_UNCHOKE_INTERVAL = 0.1
    
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
        self.host = host
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.storage = storage
        self.reader = None
        self.writer = None
        self.state = PeerState()
        self._message_loop_task: Optional[asyncio.Task] = None

        self._pending_block_futures: dict[Tuple[int, int], asyncio.Future] = {}
        self._pending_block_futures_lock = asyncio.Lock()
        
        self._write_lock = asyncio.Lock()
        
        self._pending_uploads: dict[tuple[int,int], asyncio.Task] = {}
        self._pending_uploads_lock = asyncio.Lock()

    async def connect(self) -> None:
        if self.reader is None or self.writer is None:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.CONNECTION_TIMEOUT,
            )

    async def close(self) -> None:
        await self.stop_message_loop()
        self.writer.close()
        await self.writer.wait_closed() #make sure the connection is fully closed
        self.reader = None
        self.writer = None
        self.state.reset()
        async with self._pending_block_futures_lock:
            for future in self._pending_block_futures.values():
                if not future.done():
                    future.cancel()
            self._pending_block_futures.clear()
        async with self._pending_uploads_lock:
            for task in list(self._pending_uploads.values()):
                try:
                    task.cancel()
                except Exception:
                    pass
            self._pending_uploads.clear()

    #async version of __enter__ and __exit__ ``
    async def __aenter__(self) -> "PeerConnection":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def send_handshake(self) -> None:
        await self.connect() #make sure its connected even though it should be already
        if self.writer is None or self.reader is None:
            raise ConnectionError("not connected to peer")

        handshake = protocol_encoder.pack_handshake(self.info_hash, self.peer_id)
        
        async with self._write_lock:
            self.writer.write(handshake)
            await self._drain()

        response = await self._read_exactly(68)

        _, remote_peer_id = protocol_encoder.unpack_handshake(response, expected_info_hash=self.info_hash)
        self.state.remote_peer_id = remote_peer_id

    async def send_message(self, message_id: Optional[int], payload: bytes = b"") -> None:
        await self.connect()
        if self.writer is None:
            raise ConnectionError("not connected to peer")
        if message_id is None:
            packet = protocol_encoder.pack_keepalive()
        else:
            packet = protocol_encoder.pack_message(message_id, payload)

        async with self._write_lock:
            self.writer.write(packet)
            await self._drain()       

    async def send_interested(self) -> None:
        await self.state.set_am_interested(True)
        await self.send_message(self.MESSAGE_INTERESTED)

    async def send_not_interested(self) -> None:
        await self.state.set_am_interested(False)
        await self.send_message(self.MESSAGE_NOT_INTERESTED)

    async def send_choke(self) -> None:
        await self.state.set_am_choking(True)
        await self.send_message(self.MESSAGE_CHOKE)

    async def send_unchoke(self) -> None:
        await self.state.set_am_choking(False)
        await self.send_message(self.MESSAGE_UNCHOKE)

    async def send_bitfield(self, bitfield: bytes) -> None:
        await self.send_message(self.MESSAGE_BITFIELD, bitfield)

    async def send_have(self, piece_index: int) -> None:
        payload = protocol_encoder.pack_have_payload(piece_index)
        await self.send_message(self.MESSAGE_HAVE, payload)

    async def request_block(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        await self.send_message(self.MESSAGE_REQUEST, payload)

    async def cancel_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = protocol_encoder.pack_request_payload(piece_index, begin, length)
        await self.send_message(self.MESSAGE_CANCEL, payload)

    async def read_message(self) -> tuple[Optional[int], Optional[object]]:
        await self.connect()

        length_prefix = await self._read_exactly(4)
        message_length = protocol_encoder.unpack_length_prefix(length_prefix)
        if message_length == 0:
            return None, None

        message = await self._read_exactly(message_length)

        message_id, payload = protocol_encoder.split_message_frame(message)

        if message_id == self.MESSAGE_CHOKE:
            result = await self._on_choke(payload)
        elif message_id == self.MESSAGE_UNCHOKE:
            result = await self._on_unchoke(payload)
        elif message_id == self.MESSAGE_INTERESTED:
            result = await self._on_interested(payload)
        elif message_id == self.MESSAGE_NOT_INTERESTED:
            result = await self._on_not_interested(payload)
        elif message_id == self.MESSAGE_HAVE:
            result = await self._on_have(payload)
        elif message_id == self.MESSAGE_BITFIELD:
            result = await self._on_bitfield(payload)
        elif message_id == self.MESSAGE_REQUEST:
            result = await self._on_request(payload)
        elif message_id == self.MESSAGE_PIECE:
            result = await self._on_piece(payload)
        elif message_id == self.MESSAGE_CANCEL:
            result = await self._on_cancel(payload)
        else:
            result = await self._on_unknown(payload)

        return message_id, result

    async def start_message_loop(self) -> None:
        if self._message_loop_task is not None and not self._message_loop_task.done():
            return
        self._message_loop_task = asyncio.create_task(self._message_loop())

    async def stop_message_loop(self) -> None:
        if self._message_loop_task is not None:
            self._message_loop_task.cancel()
            try:
                await self._message_loop_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._message_loop_task = None
            
    async def _message_loop(self) -> None:
        while True:
            message_id, parsed = await self.read_message()
            if message_id is None:
                continue
            if message_id == self.MESSAGE_PIECE:
                piece_index, begin, block = parsed
                await self._resolve_pending_block(piece_index, begin, block)
            elif message_id == self.MESSAGE_REQUEST:
                task = asyncio.create_task(self._send_piece(*parsed))
                async with self._pending_uploads_lock:
                    piece_index, begin, _length = parsed
                    self._pending_uploads[(piece_index, begin)] = task
            elif message_id == self.MESSAGE_BITFIELD:
                pass
            elif message_id == self.MESSAGE_HAVE:
                pass

    async def wait_for_unchoke(self) -> None:
        while True:
            if not await self.is_choked():
                return
            await asyncio.sleep(self.WAIT_FOR_UNCHOKE_INTERVAL)
    
    async def _send_piece(self, piece_index: int, begin: int, length: int) -> None:
        if piece_index < 0 or piece_index >= self.storage.total_piece_count:
            return
        if begin < 0 or length <= 0:
            return

        piece_length = self.storage.get_piece_length(piece_index)
        if begin >= piece_length:
            return

        read_length = min(length, piece_length - begin)
        data = self.storage.read_piece_bytes(piece_index, begin, read_length)
        if data is None:
            return
        payload = protocol_encoder.pack_piece_payload(piece_index, begin, data)
        try:
            await self.send_message(self.MESSAGE_PIECE, payload)
        finally:
            # cleanup pending upload record if present
            key = (piece_index, begin)
            async with self._pending_uploads_lock:
                self._pending_uploads.pop(key, None)

    async def is_choked(self) -> bool:
        return await self.state.is_peer_choking()
    
    async def is_interested(self) -> bool:
        return await self.state.is_am_interested()

    async def is_connected(self) -> bool:
        return self.reader is not None and self.writer is not None

    async def _on_choke(self, payload: bytes) -> None:
        await self.state.set_peer_choking(True)

    async def _on_unchoke(self, payload: bytes) -> None:
        await self.state.set_peer_choking(False)

    async def _on_interested(self, payload: bytes) -> None:
        await self.state.set_peer_interested(True)

    async def _on_not_interested(self, payload: bytes) -> None:
        await self.state.set_peer_interested(False)

    async def _on_have(self, payload: bytes) -> int:
        piece_index = protocol_encoder.unpack_have_payload(payload)
        await self.state.set_piece_in_bitfield(piece_index, protocol_encoder.set_piece_in_bitfield)
        return piece_index

    async def _on_bitfield(self, payload: bytes) -> bytes:
        payload = protocol_encoder.normalize_bitfield_length(payload, self.storage.total_piece_count)
        await self.state.update_bitfield(payload)
        return payload

    async def get_bitfield(self) -> Optional[bytes]:
        return await self.state.get_bitfield()

    async def _on_request(self, payload: bytes) -> tuple[int, int, int]:
        return protocol_encoder.unpack_request_payload(payload, "request")

    async def _on_piece(self, payload: bytes) -> tuple[int, int, bytes]:
        return protocol_encoder.unpack_piece_payload(payload)

    async def _on_cancel(self, payload: bytes) -> tuple[int, int, int]:
        piece_index, begin, length = protocol_encoder.unpack_request_payload(payload, "cancel")
        key = (piece_index, begin)
        async with self._pending_uploads_lock:
            task = self._pending_uploads.pop(key, None)
            if task is not None:
                task.cancel()
        return piece_index, begin, length

    async def _on_unknown(self, payload: bytes) -> bytes:
        return payload

    async def download_piece(self, piece_index: int) -> Optional[Piece]:
        if piece_index < 0 or piece_index >= self.storage.total_piece_count:
            return None

        await self.send_interested()
        await self.wait_for_unchoke()

        piece_length = self.storage.get_piece_length(piece_index)
        piece = Piece(piece_index, piece_length)
        block_size = min(self.DEFAULT_BLOCK_LENGTH, piece_length)

        #limit concurrent block request tasks
        semaphore = asyncio.Semaphore(self.MAX_IN_FLIGHT_BLOCKS_PER_PIECE)

        async def download_block(begin: int, length: int) -> tuple[int, Optional[bytes]]:
            async with semaphore:
                block = await self._request_block(piece_index, begin, length)
                return begin, block

        tasks = []

        #create concurrent download block tasks
        for begin in range(0, piece_length, block_size):
            tasks.append(asyncio.create_task(download_block(begin, min(block_size, piece_length - begin))))
            
        try:
            # process block downloads as they complete
            for completed_task in asyncio.as_completed(tasks):
                begin, block = await completed_task
                # if a block fails to download cancel the rest and abort the piece download
                if block is None:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    return None
                piece.add_block(begin, block)
        finally:
            #ensure all download tasks are cleaned up
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        return piece

    async def _request_block(self, piece_index: int, begin: int, length: int) -> Optional[bytes]:
        key = (piece_index, begin)

        #retry requesting the block up to MAX_BLOCK_RETRIES times in case of failures
        for attempt in range(self.MAX_BLOCK_RETRIES):
            loop = asyncio.get_running_loop()
            future = loop.create_future()

            #register the future for this specific block key to receive data
            async with self._pending_block_futures_lock:
                self._pending_block_futures[key] = future

            try:
                await self.request_block(piece_index, begin, length)
                return await asyncio.wait_for(future, timeout=self.BLOCK_DOWNLOAD_TIMEOUT)
            except Exception:
                if not future.done():
                    future.cancel()
                if attempt + 1 >= self.MAX_BLOCK_RETRIES:
                    raise TimeoutError(
                        f"failed to download block {begin} of piece {piece_index} from peer {self.host}:{self.port} after {self.MAX_BLOCK_RETRIES} retries"
                    )
                await self.cancel_request(piece_index, begin, length)
            finally:
                async with self._pending_block_futures_lock:
                    self._pending_block_futures.pop(key, None)

        return None

    async def _resolve_pending_block(self, piece_index: int, begin: int, block: bytes) -> None:
        key = (piece_index, begin)
        async with self._pending_block_futures_lock:
            future = self._pending_block_futures.get(key)

        if future is None or future.done():
            return

        # resolve the future with the received block bytes
        future.set_result(block)

    async def _read_exactly(self, size: int) -> bytes:
        if self.reader is None:
            raise ConnectionError("not connected to peer")
        return await asyncio.wait_for(self.reader.readexactly(size), timeout=self.CONNECTION_TIMEOUT)

    async def _drain(self) -> None:
        if self.writer is None:
            raise ConnectionError("not connected to peer")
        await asyncio.wait_for(self.writer.drain(), timeout=self.CONNECTION_TIMEOUT)

