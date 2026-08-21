import asyncio
from typing import Optional


class Piece:
    def __init__(self, index: int, length: int):
        self.index = index
        self.length = length
        self.blocks: dict[int, bytes] = {}  # offset - data
        self.is_complete_event = asyncio.Event()

    def add_block(self, offset: int, data: bytes) -> None:
        self.blocks[offset] = data
        if self.is_complete():
            self.is_complete_event.set()
    
    def get_assembled_data(self) -> bytes:
        if len(self.blocks) == 0:
            return b""
        #sort by offset and add together
        return b"".join(self.blocks[o] for o in sorted(self.blocks.keys()))

    def is_complete(self) -> bool:
        return len(self.get_assembled_data()) == self.length

    def wait_until_complete(self) -> None:
        self.is_complete_event.wait()