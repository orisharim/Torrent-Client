import asyncio


class Piece:
    def __init__(self, index: int, length: int, block_length: int):
        self.index = index
        self.length = length
        self.block_length = block_length
        self.blocks: dict[int, bytes | None] = {}  # offset -> data
        for offset in range(0, length, block_length):
            self.blocks[offset] = None
        self.block_received_event = asyncio.Event()

    def add_block(self, offset: int, data: bytes) -> bool:
        if offset not in self.blocks or not data:
            return False
        if self.blocks[offset] is not None:
            return False
        expected_length = min(self.block_length, self.length - offset)
        if len(data) != expected_length:
            return False
        self.blocks[offset] = data
        self.block_received_event.set()
        return True

    def get_assembled_data(self) -> bytes:
        if len(self.blocks) == 0:
            return b""
        #sort by offset and add together
        return b"".join(self.blocks[o] for o in sorted(self.blocks.keys()))

    def is_complete(self) -> bool:
        return self.get_received_block_count() >= self.get_block_count()

    def get_block_count(self) -> int:
        return len(self.blocks)

    def get_received_block_count(self) -> int:
        count = 0
        for block in self.blocks.values():
            if block is not None and len(block) > 0:
                count += 1
        return count

    def get_received_byte_count(self) -> int:
        return sum(len(block) for block in self.blocks.values() if block is not None)