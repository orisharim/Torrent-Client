class Piece:
    def __init__(self, index: int, length: int):
        self.index = index
        self.length = length
        self.blocks = dict()  # begin -> bytes
        self.downloaded = 0
        