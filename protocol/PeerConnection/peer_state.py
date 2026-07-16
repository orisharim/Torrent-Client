import asyncio
from typing import Optional


class PeerState:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.reset()

    def reset(self) -> None:
        self.remote_peer_id: Optional[bytes] = None
        self.bitfield: Optional[bytes] = None
        
        self.am_choking = True
        self.am_interested = False
        
        self.peer_choking = True
        self.peer_interested = False

    async def update_bitfield(self, bitfield: Optional[bytes]) -> None:
        async with self.lock:
            self.bitfield = bitfield

    async def set_piece_in_bitfield(self, piece_index: int, set_in_bitfield_fn) -> None:
        async with self.lock:
            self.bitfield = set_in_bitfield_fn(self.bitfield, piece_index)

    async def get_bitfield(self) -> Optional[bytes]:
        async with self.lock:
            return self.bitfield

    async def set_am_choking(self, value: bool) -> None:
        async with self.lock:
            self.am_choking = value

    async def set_am_interested(self, value: bool) -> None:
        async with self.lock:
            self.am_interested = value

    async def set_peer_choking(self, value: bool) -> None:
        async with self.lock:
            self.peer_choking = value

    async def set_peer_interested(self, value: bool) -> None:
        async with self.lock:
            self.peer_interested = value

    async def is_peer_choking(self) -> bool:
        async with self.lock:
            return self.peer_choking

    async def is_am_interested(self) -> bool:
        async with self.lock:
            return self.am_interested