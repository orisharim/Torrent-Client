import asyncio
import struct
from typing import Optional


class PeerConnection:
    PROTOCOL_NAME = b"BitTorrent protocol"
    PROTOCOL_LENGTH = len(PROTOCOL_NAME)
    DEFAULT_BLOCK_LENGTH = 16 * 1024
    CONNECTION_TIMEOUT = 10.0

    MESSAGE_CHOKE = 0
    MESSAGE_UNCHOKE = 1
    MESSAGE_INTERESTED = 2
    MESSAGE_NOT_INTERESTED = 3
    MESSAGE_HAVE = 4
    MESSAGE_BITFIELD = 5
    MESSAGE_REQUEST = 6
    MESSAGE_PIECE = 7
    MESSAGE_CANCEL = 8

    def __init__(self, host: str, port: int, info_hash: bytes, peer_id: bytes) -> None:
        self.host = host
        self.port = port
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.reader = None
        self.writer = None
        self.remote_peer_id: Optional[bytes] = None
        self.bitfield: Optional[bytes] = None
        self.choked = True
        self.interested = False

    async def connect(self) -> None:
        if self.reader is None or self.writer is None:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.CONNECTION_TIMEOUT,
            )

    async def close(self) -> None:
        if self.writer is None:
            return
        self.writer.close()
        await self.writer.wait_closed() #make sure the connection is fully closed

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

        self.writer.write(packet)
        await self._drain()

    async def read_message(self) -> tuple[Optional[int], bytes]:
        await self.connect()

        length_prefix = await self._read_exactly(4)
        (message_length,) = struct.unpack(">I", length_prefix)
        if message_length == 0:
            return None, b""

        message = await self._read_exactly(message_length)
        return message[0], message[1:]

    async def read_bitfield(self) -> bytes:
        message_id, payload = await self.read_message()
        if message_id != self.MESSAGE_BITFIELD:
            raise ValueError("expected bitfield message")

        self.bitfield = payload
        return payload

    async def send_interested(self) -> None:
        self.interested = True
        await self.send_message(self.MESSAGE_INTERESTED)

    async def send_not_interested(self) -> None:
        self.interested = False
        await self.send_message(self.MESSAGE_NOT_INTERESTED)

    async def send_choke(self) -> None:
        self.choked = True
        await self.send_message(self.MESSAGE_CHOKE)

    async def send_unchoke(self) -> None:
        self.choked = False
        await self.send_message(self.MESSAGE_UNCHOKE)

    async def send_have(self, piece_index: int) -> None:
        payload = struct.pack(">I", piece_index)
        await self.send_message(self.MESSAGE_HAVE, payload)

    async def request_block(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = struct.pack(">III", piece_index, begin, length)
        await self.send_message(self.MESSAGE_REQUEST, payload)

   
    async def cancel_request(self, piece_index: int, begin: int, length: int = DEFAULT_BLOCK_LENGTH) -> None:
        payload = struct.pack(">III", piece_index, begin, length)
        await self.send_message(self.MESSAGE_CANCEL, payload)

    async def read_block(self) -> tuple[int, int, bytes]:
        message_id, payload = await self.read_message()
        if message_id != self.MESSAGE_PIECE:
            raise ValueError("expected piece message")
        if len(payload) < 8:
            raise ValueError("invalid piece payload")

        piece_index, begin = struct.unpack(">II", payload[:8])
        block = payload[8:]
        return piece_index, begin, block
    
    
    #wrap them with timeout to prevent hanging if the peer is unresponsive
    async def _read_exactly(self, size: int) -> bytes:
        if self.reader is None:
            raise ConnectionError("not connected to peer")
        return await asyncio.wait_for(self.reader.readexactly(size), timeout=self.CONNECTION_TIMEOUT)

    async def _drain(self) -> None:
        if self.writer is None:
            raise ConnectionError("not connected to peer")
        await asyncio.wait_for(self.writer.drain(), timeout=self.CONNECTION_TIMEOUT)
