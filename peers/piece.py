from typing import Optional


class Piece:
    def __init__(self, index: int, blocks: list[tuple[int, int, bytes]]):
        self.index = index
        self.length = len(blocks)
        self.blocks = blocks
        self.peers_count = 0

    def get_block(self, begin: int) -> Optional[bytes]:
        for _piece_index, block_begin, block_data in self.blocks:
            if block_begin == begin:
                return block_data
        return None
    
        