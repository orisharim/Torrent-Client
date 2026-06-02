import asyncio
import struct
from typing import Optional, Tuple
from collections import deque
import fcntl

from peers.torrent_storage import TorrentStorage

class PeerConnection:
    PROTOCOL_NAME = b"BitTorrent protocol"
    PROTOCOL_LENGTH = len(PROTOCOL_NAME)
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
    PENDING_BLOCKS_LIMIT = 1024

    def __init__(self, host: str, port: int, info_hash: bytes, peer_id: bytes, storage: TorrentStorage) -> None:
        self.host = host
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.storage = storage
        self.reader = None
        self.writer = None
        self.remote_peer_id: Optional[bytes] = None
        self.bitfield: Optional[bytes] = None
        self.choked = True
        self.interested = False
        self._message_loop_task: Optional[asyncio.Task] = None
        self._incoming_pieces: asyncio.Queue = asyncio.Queue()
        self._pending_blocks: dict[Tuple[int, int], bytes] = {}
        self._pending_blocks_queue: deque[Tuple[int, int]] = deque()
        self._pending_blocks_lock = asyncio.Lock()
        self._choked_lock = asyncio.Lock()
        self._interested_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._bitfield_lock = asyncio.Lock()
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
        self.remote_peer_id = None
        async with self._bitfield_lock:
            self.bitfield = None
        async with self._choked_lock:
            self.choked = True
        async with self._interested_lock:
            self.interested = False
        async with self._pending_blocks_lock:
            self._pending_blocks.clear()
            self._pending_blocks_queue.clear()
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

    async def send_handshake(self) -> bytes:
        await self.connect() #make sure its connected even though it should be already
        if self.writer is None or self.reader is None:
            raise ConnectionError("not connected to peer")

        handshake = struct.pack(
            ">B19s8s20s20s",
            self.PROTOCOL_LENGTH,
            self.PROTOCOL_NAME,
            b"\x00" * 8,
            self.info_hash,
            self.peer_id,
        )
        async with self._write_lock:
            self.writer.write(handshake)
            await self._drain()

        response = await self._read_exactly(68)
        pstrlen, protocol_name, _reserved, info_hash, peer_id = struct.unpack(
            ">B19s8s20s20s", response
        )

        if pstrlen != self.PROTOCOL_LENGTH or protocol_name != self.PROTOCOL_NAME:
            raise ValueError("invalid BitTorrent handshake from peer")
        if info_hash != self.info_hash:
            raise ValueError("peer responded with a different info_hash")

        self.remote_peer_id = peer_id
        return peer_id

    async def send_message(self, message_id: Optional[int], payload: bytes = b"") -> None:
        await self.connect()
        if self.writer is None:
            raise ConnectionError("not connected to peer")
        if message_id is None:
            packet = struct.pack(">I", 0)
        else:
            packet = struct.pack(">IB", len(payload) + 1, message_id) + payload

        async with self._write_lock:
            self.writer.write(packet)
            await self._drain()       

    async def send_interested(self) -> None:
        async with self._interested_lock:
            self.interested = True
        await self.send_message(self.MESSAGE_INTERESTED)

    async def send_not_interested(self) -> None:
        async with self._interested_lock:
            self.interested = False
        await self.send_message(self.MESSAGE_NOT_INTERESTED)

    async def send_choke(self) -> None:
        async with self._choked_lock:
            self.choked = True
        await self.send_message(self.MESSAGE_CHOKE)

    async def send_unchoke(self) -> None:
        async with self._choked_lock:
            self.choked = False
        await self.send_message(self.MESSAGE_UNCHOKE)

    async def send_bitfield(self, bitfield: bytes) -> None:
        await self.send_message(self.MESSAGE_BITFIELD, bitfield)

    async def send_have(self, piece_index: int) -> None:
        payload = struct.pack(">I", piece_index)
        await self.send_message(self.MESSAGE_HAVE, payload)

    async def request_block(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = struct.pack(">III", piece_index, begin, length)
        await self.send_message(self.MESSAGE_REQUEST, payload)

    async def cancel_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = struct.pack(">III", piece_index, begin, length)
        await self.send_message(self.MESSAGE_CANCEL, payload)

    async def read_message(self) -> tuple[Optional[int], Optional[object]]:
        await self.connect()

        length_prefix = await self._read_exactly(4)
        (message_length,) = struct.unpack(">I", length_prefix)
        if message_length == 0:
            return None, None

        message = await self._read_exactly(message_length)
        
        if message is None or len(message) == 0:
            return None, None
        
        message_id = message[0]
        payload = message[1:]
        
        handler_map = {
            self.MESSAGE_CHOKE: self._on_choke,
            self.MESSAGE_UNCHOKE: self._on_unchoke,
            self.MESSAGE_INTERESTED: self._on_interested,
            self.MESSAGE_NOT_INTERESTED: self._on_not_interested,
            self.MESSAGE_HAVE: self._on_have,
            self.MESSAGE_BITFIELD: self._on_bitfield,
            self.MESSAGE_REQUEST: self._on_request,
            self.MESSAGE_PIECE: self._on_piece,
            self.MESSAGE_CANCEL: self._on_cancel,
        }

        handler = handler_map.get(message_id, self._on_unknown)
        result = await handler(payload)
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
        try:
            while True:
                message_id, parsed = await self.read_message()
                if message_id is None:
                    continue
                if message_id == self.MESSAGE_PIECE:
                    # parsed is (piece_index, begin, block)
                    await self._incoming_pieces.put(parsed)
                elif message_id == self.MESSAGE_REQUEST:
                    # parsed is (piece_index, begin, length)
                    task = asyncio.create_task(self._send_piece(*parsed))
                    async with self._pending_uploads_lock:
                        try:
                            piece_index, begin, length = parsed
                            self._pending_uploads[(piece_index, begin)] = task
                        except Exception:
                            pass
                elif message_id == self.MESSAGE_BITFIELD:
                    pass
                elif message_id == self.MESSAGE_HAVE:
                    # parsed is piece_index
                    pass
        except Exception as e:
            # log and exit message loop on unexpected errors
            print(f"PeerConnection message loop exiting for {self.host}:{self.port}: {e}")
            return

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
        payload = struct.pack(">II", piece_index, begin) + data
        try:
            await self.send_message(self.MESSAGE_PIECE, payload)
        finally:
            # cleanup pending upload record if present
            key = (piece_index, begin)
            async with self._pending_uploads_lock:
                self._pending_uploads.pop(key, None)

    async def is_choked(self) -> bool:
        async with self._choked_lock:
            return self.choked
    
    async def is_interested(self) -> bool:
        async with self._interested_lock:
            return self.interested

    async def is_connected(self) -> bool:
        return self.reader is not None and self.writer is not None

    async def _on_choke(self, payload: bytes) -> None:
        async with self._choked_lock:
            self.choked = True

    async def _on_unchoke(self, payload: bytes) -> None:
        async with self._choked_lock:
            self.choked = False

    async def _on_interested(self, payload: bytes) -> None:
        async with self._interested_lock:
            self.interested = True

    async def _on_not_interested(self, payload: bytes) -> None:
        async with self._interested_lock:
            self.interested = False

    async def _on_have(self, payload: bytes) -> int:
        if len(payload) != 4:
            raise ValueError("invalid have payload")
        (piece_index,) = struct.unpack(">I", payload)
        # Update bitfield to reflect that remote peer has this piece
        byte_index = piece_index // 8
        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)
        async with self._bitfield_lock:
            if self.bitfield is None:
                # create a bitfield large enough to hold this piece
                self.bitfield = b"\x00" * (byte_index + 1)
            elif byte_index >= len(self.bitfield):
                self.bitfield += b"\x00" * (byte_index - len(self.bitfield) + 1)

            self.bitfield = (
                self.bitfield[:byte_index]
                + bytes([self.bitfield[byte_index] | mask])
                + self.bitfield[byte_index + 1:]
            )

        return piece_index

    async def _on_bitfield(self, payload: bytes) -> bytes:
        # Normalize bitfield length to storage's total_piece_count
        expected_len = (self.storage.total_piece_count + 7) // 8
        if len(payload) < expected_len:
            payload = payload + b"\x00" * (expected_len - len(payload))
        elif len(payload) > expected_len:
            payload = payload[:expected_len]

        async with self._bitfield_lock:
            self.bitfield = payload
        return payload

    async def get_bitfield(self) -> Optional[bytes]:
        async with self._bitfield_lock:
            return self.bitfield

    async def _on_request(self, payload: bytes) -> tuple[int, int, int]:
        if len(payload) != 12:
            raise ValueError("invalid request payload")
        piece_index, begin, length = struct.unpack(">III", payload)
        return piece_index, begin, length

    async def _on_piece(self, payload: bytes) -> tuple[int, int, bytes]:
        if len(payload) < 8:
            raise ValueError("invalid piece payload")
        piece_index, begin = struct.unpack(">II", payload[:8])
        block = payload[8:]
        return piece_index, begin, block

    async def _on_cancel(self, payload: bytes) -> tuple[int, int, int]:
        if len(payload) != 12:
            raise ValueError("invalid cancel payload")
        piece_index, begin, length = struct.unpack(">III", payload)
        key = (piece_index, begin)
        async with self._pending_uploads_lock:
            task = self._pending_uploads.pop(key, None)
            if task is not None:
                task.cancel()
        return piece_index, begin, length

    async def _on_unknown(self, payload: bytes) -> bytes:
        return payload
      
    async def _read_exactly(self, size: int) -> bytes:
        if self.reader is None:
            raise ConnectionError("not connected to peer")
        return await asyncio.wait_for(self.reader.readexactly(size), timeout=self.CONNECTION_TIMEOUT)

    async def _drain(self) -> None:
        if self.writer is None:
            raise ConnectionError("not connected to peer")
        await asyncio.wait_for(self.writer.drain(), timeout=self.CONNECTION_TIMEOUT)

    async def read_block(self, piece_index: int, begin: int, length: int) -> bytes:
        key = (piece_index, begin)
        async with self._pending_blocks_lock:
            if key in self._pending_blocks:
                # remove key from queue and return data
                data = self._pending_blocks.pop(key)
                try:
                    self._pending_blocks_queue.remove(key)
                except ValueError:
                    pass
                return data

        while True:
            item = await self._incoming_pieces.get()
            if item is None:
                continue
            try:
                pi, bgn, block = item
            except Exception:
                continue

            if (pi, bgn) == key:
                return block

            async with self._pending_blocks_lock:
                while len(self._pending_blocks) >= self.PENDING_BLOCKS_LIMIT:
                    try:
                        old_key = self._pending_blocks_queue.popleft()
                        self._pending_blocks.pop(old_key, None)
                    except IndexError:
                        break
                self._pending_blocks[(pi, bgn)] = block
                self._pending_blocks_queue.append((pi, bgn))

        