from pathlib import Path
from typing import Optional
import asyncio
import fcntl
from piece import Piece
DEFAULT_BLOCK_LENGTH = 16 * 1024


class TorrentStorage:
    def __init__(self, piece_length: int, total_piece_count: int, files: list[tuple[list[str], int]] | None = None, base_path: str = "downloads"):
        """
        Initialize TorrentStorage for single or multi-file torrents.
        
        Args:
            piece_length: The length of each piece in bytes
            total_piece_count: Total number of pieces in the torrent
            files: List of (path_parts, file_length) tuples. If None, assumes single file.
            base_path: Base directory for storing downloaded files
        """
        self.piece_length = piece_length
        self.total_piece_count = total_piece_count
        self.base_path = Path(base_path)
        self.downloaded_pieces: set[int] = set()
        self._downloaded_pieces_lock = asyncio.Lock()
        
        self.files = files or [(["download"], piece_length * total_piece_count)]
        self._build_file_offset_map()
    
    def _build_file_offset_map(self) -> None:
        """Build a map of file offsets for piece to file mapping."""
        self.file_offsets: list[tuple[Path, int, int]] = []  # (path, start_offset, length)
        cumulative_offset = 0
        
        for filename, file_length in self.files:
            file_path = self.base_path.joinpath(*filename)
            self.file_offsets.append((file_path, cumulative_offset, file_length))
            cumulative_offset += file_length
    
    def _get_piece_location(self, piece_index: int) -> tuple[int, int]:
        start_offset = piece_index * self.piece_length
        piece_length = self.get_piece_length(piece_index)
        return start_offset, start_offset + piece_length
    
    def _get_file_spans_for_range(self, range_start: int, range_end: int) -> list[tuple[Path, int, int]]:
        """
        Get the files and offsets that a global offset range spans across.
        Returns list of (file_path, file_offset, bytes_count)
        """
        spans: list[tuple[Path, int, int]] = []
        
        for file_path, file_start_offset, file_length in self.file_offsets:
            file_end_offset = file_start_offset + file_length
            
            # Check if range overlaps with this file
            if range_start < file_end_offset and range_end > file_start_offset:
                overlap_start = max(range_start, file_start_offset)
                overlap_end = min(range_end, file_end_offset)
                bytes_count = overlap_end - overlap_start
                file_offset = overlap_start - file_start_offset
                spans.append((file_path, file_offset, bytes_count))
        
        return spans
    
    def _get_file_spans_for_piece(self, piece_index: int) -> list[tuple[Path, int, int]]:
        """
        Get the files and offsets that a piece spans across.
        Returns list of (file_path, file_offset, bytes_to_write)
        """
        piece_start, piece_end = self._get_piece_location(piece_index)
        return self._get_file_spans_for_range(piece_start, piece_end)
    
    async def add_piece(self, piece_index: int,begin: Optional[int] , block_data: bytes) -> None:
        if self._write_piece_to_disk(piece_index, begin, block_data):
            async with self._downloaded_pieces_lock:
                self.downloaded_pieces.add(piece_index)
    
    def _write_piece_to_disk(self, piece_index: int, begin: Optional[int] ,data: bytes) -> bool:
        file_spans = self._get_file_spans_for_piece(piece_index)
        bytes_written = 0

        if begin is not None:
            piece_start, _ = self._get_piece_location(piece_index)
            range_start = piece_start + begin
            range_end = range_start + len(data)
            file_spans = self._get_file_spans_for_range(range_start, range_end)
        
        for file_path, file_offset, bytes_count in file_spans:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'rb+' if file_path.exists() else 'wb'
            
            with open(file_path, mode) as f:
                # File locking to prevent concurrent writes
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.seek(file_offset)
                    chunk = data[bytes_written:bytes_written + bytes_count]
                    f.write(chunk)
                    bytes_written += bytes_count
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        return True

    async def restore_pieces_from_disk(self) -> None:
        for idx in range(self.total_piece_count):
            data = self._read_piece_from_disk(idx)
            if data:
                async with self._downloaded_pieces_lock:
                    self.downloaded_pieces.add(idx)
    
    def _read_piece_from_disk(self, piece_index: int) -> Optional[bytes]:
        file_spans = self._get_file_spans_for_piece(piece_index)
        piece_data = bytearray()
        
        for file_path, file_offset, bytes_count in file_spans:
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                # File locking to prevent reading while writing
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    f.seek(file_offset)
                    chunk = f.read(bytes_count)
                    if len(chunk) < bytes_count:
                        return None  # File doesn't have enough data
                    piece_data.extend(chunk)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        return bytes(piece_data) if piece_data else None
    
    def read_piece_bytes(self, piece_index: int, begin: int, length: int) -> Optional[bytes]:
        """Read a portion of a piece from disk."""
        piece_start, _ = self._get_piece_location(piece_index)
        piece_length = self.get_piece_length(piece_index)
        
        if begin < 0 or length <= 0 or begin >= piece_length:
            return None
        
        read_length = min(length, piece_length - begin)
        range_start = piece_start + begin
        range_end = range_start + read_length
        
        file_spans = self._get_file_spans_for_range(range_start, range_end)
        piece_data = bytearray()
        
        for file_path, file_offset, bytes_count in file_spans:
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                # File locking to prevent reading while writing
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    f.seek(file_offset)
                    chunk = f.read(bytes_count)
                    if len(chunk) < bytes_count:
                        return None  # File doesn't have enough data
                    piece_data.extend(chunk)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        return bytes(piece_data) if piece_data else None

    def get_piece_length(self, piece_index: int) -> int:
        """Return the actual length of a piece, including the final partial piece."""
        if piece_index < 0 or piece_index >= self.total_piece_count:
            raise IndexError("piece_index out of range")

        total_length = sum(file_length for _, file_length in self.files)
        piece_start = piece_index * self.piece_length
        remaining = total_length - piece_start
        return min(self.piece_length, max(0, remaining))
        
        
    
        