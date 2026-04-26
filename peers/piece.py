from pyparsing import Optional


class Piece:
    def __init__(self, index: int, length: int):
        self.index = index
        self.length = length
        self.blocks = dict()  # begin/offset -> bytes
        self.peers_count = 0

    def get_block(self, begin: int) -> Optional[bytes]:
        return self.blocks.get(begin)
    
        