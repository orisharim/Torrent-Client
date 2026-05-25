from typing import Optional

from peers.peer_connection import PeerConnection


class Piece:
    def __init__(self, index: int, length: int):
        self.index = index
        self.length = length
        self.blocks: dict[int, bytes] = {}  # offset - data
    
    def add_block(self, offset: int, data: bytes) -> None:
        self.blocks[offset] = data
    
    def get_assembled_data(self) -> bytes:
        if len(self.blocks) == 0:
            return b""
        #sort by offset and add together
        return b"".join(self.blocks[o] for o in sorted(self.blocks.keys()))