from typing import Optional

from peers.peer_connection import PeerConnection


class Piece:
    def __init__(self, blocks: list[tuple[int, int, bytes]]):
        self.length = len(blocks)
        self.blocks = blocks
        self.peers_count = 0

    def get_assembled_data(self) -> bytes:
        return b"".join(block for _, _, block in self.blocks)
    