from hashlib import sha1
from pathlib import Path
from typing import Optional
import asyncio
import fcntl
from piece import Piece
from torrent import Torrent
DEFAULT_BLOCK_LENGTH = 16 * 1024


class TorrentStorage:
    def __init__(self, torrent_metadata: Torrent, base_path: str = "downloads"):
    
        self._piece_length = torrent_metadata.piece_length
        self._torrent_metadata = torrent_metadata
        self._total_piece_count = len(torrent_metadata.pieces)
        self._base_path = Path(base_path)
        self._downloaded_pieces: set[int] = set()
        self._downloaded_pieces_lock = asyncio.Lock()
        
        self.files = torrent_metadata.files or [(["download"], self._piece_length * self._total_piece_count)]
        self._build_file_offset_map()

    def get_downloaded_pieces(self) -> set[int]:
        self.restore_pieces_from_disk()
        return self._downloaded_pieces
    
    def _build_file_offset_map(self) -> None:
        """Build a map of file offsets for piece to file mapping."""
        self.file_offsets: list[tuple[Path, int, int]] = []  # (path, start_offset, length)
        cumulative_offset = 0
        
        for filename, file_length in self.files:
            file_path = self._base_path.joinpath(*filename)
            self.file_offsets.append((file_path, cumulative_offset, file_length))
            cumulative_offset += file_length
    
    def _get_piece_location(self, piece_index: int) -> tuple[int, int]:
        start_offset = piece_index * self._piece_length
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
        if await self._write_piece_to_disk(piece_index, begin, block_data):
            async with self._downloaded_pieces_lock:
                self._downloaded_pieces.add(piece_index)

    async def delete_piece(self, piece_index: int) -> None:
        file_spans = self._get_file_spans_for_piece(piece_index)
        
        for file_path, file_offset, bytes_count in file_spans:
            if not file_path.exists():
                continue
            
            with open(file_path, 'r+b') as f:
                # File locking to prevent concurrent writes
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.seek(file_offset)
                    f.write(b"\x00" * bytes_count)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        async with self._downloaded_pieces_lock:
            self._downloaded_pieces.discard(piece_index)

    async def _validate_piece(self, piece_index: int) -> bool:
        assembled_piece = await self._read_piece_from_disk(piece_index)
        if assembled_piece is None:
            return False
        piece_hash = sha1(assembled_piece).digest()
        if piece_index < 0 or piece_index >= self._total_piece_count:
            return False
    
        expected_hash = self._torrent_metadata.pieces[piece_index]
        return piece_hash == expected_hash

    def delete_broken_pieces(self) -> None:
        for piece_index in list(self._downloaded_pieces):
            if not self._validate_piece(piece_index):
                self.delete_piece(piece_index)

    def is_complete(self) -> bool:
        for piece_index in range(self._total_piece_count):
            if not self._validate_piece(piece_index):
                return False
        return True
    
    async def _write_piece_to_disk(self, piece_index: int, begin: Optional[int] ,data: bytes) -> bool:
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
        for idx in range(self._total_piece_count):
            data = await self._read_piece_from_disk(idx)
            if data:
                async with self._downloaded_pieces_lock:
                    self._downloaded_pieces.add(idx)
    
    async def _read_piece_from_disk(self, piece_index: int) -> Optional[bytes]:
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
        if piece_index < 0 or piece_index >= self._total_piece_count:
            raise IndexError("piece_index out of range")

        total_length = sum(file_length for _, file_length in self.files)
        piece_start = piece_index * self._piece_length
        remaining = total_length - piece_start
        return min(self._piece_length, max(0, remaining))
        
        
    
        