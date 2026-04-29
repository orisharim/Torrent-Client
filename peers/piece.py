from typing import Optional

from peers.peer_connection import PeerConnection


class Piece:
    def __init__(self, blocks: list[tuple[int, int, bytes]]):
        self.length = len(blocks)
        self.blocks = blocks
        self.peers_count = 0

    def get_assembled_data(self) -> bytes:
        return b"".join(block for _, _, block in self.blocks)
    
class FileStorage:
    def __init__(self, piece_length: int, total_piece_count: int):
        #TODO: make this code handle multiple files not just one
        
        self.downloaded_pieces: dict[int, Piece] = {}
        self.total_piece_count = total_piece_count
        self.piece_length = piece_length
    
    def _add_piece(self, piece: Piece) -> None:
        if(self._write_to_disk(self._get_piece_path(piece.index), piece.index * self.piece_length, piece.get_assembled_data())):
            self.downloaded_pieces[piece.index] = piece
        
    
    def _write_to_disk(self, path, offset, chunk) -> bool:
        
        path.parent.mkdir(parents=True, exist_ok=True)#ensure the directory exists
        mode = 'rb+' if path.exists() else 'wb'
        
        with open(path, mode) as f:
            f.seek(offset)
            f.write(chunk)
            return True
        return False 
    
    
    
    def restore_pieces_from_disk(self) -> None:
    #"""Restores pieces from disk into memory. This should be useful for resuming downloads."""
        for idx in range(self.total_piece_count):
            path = self._get_piece_path(idx)
            if path.exists():
                with open(path, 'rb') as f:
                    data = f.read()
                    blocks = []
                    for i in range(0, len(data), PeerConnection.DEFAULT_BLOCK_LENGTH):
                        block = data[i:i+PeerConnection.DEFAULT_BLOCK_LENGTH]
                        blocks.append((idx, i, block))
                    piece = Piece(blocks)
                    self.downloaded_pieces[idx] = piece
        
        
    
        