from hashlib import sha1
from pathlib import Path
from typing import Optional
import asyncio
import fcntl
import os
from torrent import Torrent
import peers.peer_protocol_encoder as protocol_encoder

DEFAULT_BLOCK_LENGTH = 16 * 1024


def _write_spans_sync(file_spans: list[tuple[Path, int, int]], data: bytes) -> None:
    """Synchronously write blocks to specified file spans, acquiring an exclusive lock."""
    bytes_written = 0
    for file_path, file_offset, bytes_count in file_spans:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.touch()
        with open(file_path, "r+b") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(file_offset)
                chunk = data[bytes_written : bytes_written + bytes_count]
                f.write(chunk)
                bytes_written += bytes_count
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _delete_spans_sync(file_spans: list[tuple[Path, int, int]]) -> None:
    """Synchronously overwrite file spans with null bytes, acquiring an exclusive lock."""
    for file_path, file_offset, bytes_count in file_spans:
        if not file_path.exists():
            continue
        with open(file_path, "r+b") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(file_offset)
                f.write(b"\x00" * bytes_count)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _read_spans_sync(file_spans: list[tuple[Path, int, int]]) -> Optional[bytes]:
    """Synchronously read chunks from file spans, acquiring a shared lock."""
    piece_data = bytearray()
    for file_path, file_offset, bytes_count in file_spans:
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                f.seek(file_offset)
                chunk = f.read(bytes_count)
                if len(chunk) < bytes_count:
                    return None  # File does not have enough data
                piece_data.extend(chunk)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return bytes(piece_data) if piece_data else None


class TorrentStorage:
    def __init__(self, torrent_metadata: Torrent, base_path: str = "downloads"):
        self._piece_length = torrent_metadata.piece_length
        self._torrent_metadata = torrent_metadata
        self._total_piece_count = len(torrent_metadata.pieces)
        self._base_path = Path(base_path)
        self._downloaded_pieces: set[int] = set()
        self._downloaded_pieces_lock = asyncio.Lock()
        self._bitfield: bytes = protocol_encoder.generate_empty_bitfield(
            total_piece_count=self._total_piece_count
        )
        self._bitfield_lock = asyncio.Lock()

        self.files = torrent_metadata.files_info
        self._build_file_offset_map()

    async def get_downloaded_pieces(self) -> set[int]:
        """Get the set of downloaded piece indices."""
        async with self._downloaded_pieces_lock:
            return set(self._downloaded_pieces)

    async def is_piece_downloaded(self, piece_index: int) -> bool:
        """Check if a specific piece has been downloaded."""
        async with self._downloaded_pieces_lock:
            return piece_index in self._downloaded_pieces

    async def has_piece(self, piece_index: int) -> bool:
        """Check if a specific piece has been downloaded. (Alias for is_piece_downloaded)"""
        async with self._downloaded_pieces_lock:
            return piece_index in self._downloaded_pieces

    def get_bitfield(self) -> bytes:
        """Get the current bitfield representing downloaded pieces."""
        return self._bitfield

    async def set_piece_in_bitfield(self, piece_index: int) -> None:
        """Set a piece as downloaded in the bitfield."""
        async with self._bitfield_lock:
            self._bitfield = protocol_encoder.set_piece_in_bitfield(
                self._bitfield, piece_index
            )

    async def clear_piece_in_bitfield(self, piece_index: int) -> None:
        """Clear a piece from the bitfield."""
        async with self._bitfield_lock:
            self._bitfield = protocol_encoder.clear_piece_in_bitfield(
                self._bitfield, piece_index
            )

    def _build_file_offset_map(self) -> None:
        """Build a map of file offsets for piece-to-file mapping."""
        self.file_offsets: list[tuple[Path, int, int]] = []
        cumulative_offset = 0

        for filename, file_length in self.files:
            file_path = self._base_path.joinpath(*filename)
            self.file_offsets.append((file_path, cumulative_offset, file_length))
            cumulative_offset += file_length

    def _get_piece_location(self, piece_index: int) -> tuple[int, int]:
        """Get the absolute start and end offsets of a piece."""
        start_offset = piece_index * self._piece_length
        piece_length = self.get_piece_length(piece_index)
        return start_offset, start_offset + piece_length

    def _get_file_spans_for_range(
        self, range_start: int, range_end: int
    ) -> list[tuple[Path, int, int]]:
        """
        Get the files and offsets that a global offset range spans across.
        Returns a list of (file_path, file_offset, bytes_count).
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

    def _get_file_spans_for_piece(
        self, piece_index: int
    ) -> list[tuple[Path, int, int]]:
        """
        Get the files and offsets that a piece spans across.
        Returns a list of (file_path, file_offset, bytes_to_write).
        """
        piece_start, piece_end = self._get_piece_location(piece_index)
        return self._get_file_spans_for_range(piece_start, piece_end)

    async def add_piece(
        self, piece_index: int, begin: Optional[int], block_data: bytes
    ) -> None:
        """Write piece data to disk and update internal structures."""
        if await self._write_piece_to_disk(piece_index, begin, block_data):
            async with self._downloaded_pieces_lock:
                self._downloaded_pieces.add(piece_index)
            await self.set_piece_in_bitfield(piece_index)

    async def delete_piece(self, piece_index: int) -> None:
        """Fill the disk space of the piece with zeros and clear download records."""
        file_spans = self._get_file_spans_for_piece(piece_index)
        await asyncio.to_thread(_delete_spans_sync, file_spans)

        async with self._downloaded_pieces_lock:
            self._downloaded_pieces.discard(piece_index)
        await self.clear_piece_in_bitfield(piece_index)

    async def _validate_piece(self, piece_index: int) -> bool:
        """Verify the integrity of a piece by checking its SHA1 digest."""
        if piece_index < 0 or piece_index >= self._total_piece_count:
            return False

        assembled_piece = await self._read_piece_from_disk(piece_index)
        if assembled_piece is None:
            return False

        piece_hash = sha1(assembled_piece).digest()
        expected_hash = self._torrent_metadata.pieces[piece_index]
        return piece_hash == expected_hash

    async def delete_broken_pieces(self) -> None:
        """Validate all downloaded pieces and delete any that are corrupted."""
        async with self._downloaded_pieces_lock:
            pieces_to_check = list(self._downloaded_pieces)

        for piece_index in pieces_to_check:
            if not await self._validate_piece(piece_index):
                await self.delete_piece(piece_index)

    def is_complete(self) -> bool:
        """Check if all pieces in the torrent have been downloaded."""
        return len(self._downloaded_pieces) == self._total_piece_count

    async def _write_piece_to_disk(
        self, piece_index: int, begin: Optional[int], data: bytes
    ) -> bool:
        """Write a block of piece data to the corresponding files asynchronously."""
        file_spans = self._get_file_spans_for_piece(piece_index)

        if begin is not None:
            piece_start, _ = self._get_piece_location(piece_index)
            range_start = piece_start + begin
            range_end = range_start + len(data)
            file_spans = self._get_file_spans_for_range(range_start, range_end)

        await asyncio.to_thread(_write_spans_sync, file_spans, data)
        return True

    async def restore_pieces_from_disk(self) -> None:
        """Scan the disk for existing files and mark valid pieces as downloaded."""
        any_file_exists = False
        for file_path, _, _ in self.file_offsets:
            if file_path.exists() and file_path.stat().st_size > 0:
                any_file_exists = True
                break
        
        if not any_file_exists:
            return

        for idx in range(self._total_piece_count):
            if await self._validate_piece(idx):
                async with self._downloaded_pieces_lock:
                    self._downloaded_pieces.add(idx)
                await self.set_piece_in_bitfield(idx)

    def get_total_piece_count(self) -> int:
        """Get the total number of pieces in the torrent."""
        return self._total_piece_count

    async def _read_piece_from_disk(self, piece_index: int) -> Optional[bytes]:
        """Read an entire piece from disk asynchronously."""
        file_spans = self._get_file_spans_for_piece(piece_index)
        return await asyncio.to_thread(_read_spans_sync, file_spans)

    def read_piece_bytes(
        self, piece_index: int, begin: int, length: int
    ) -> Optional[bytes]:
        """Read a portion of a piece from disk synchronously."""
        piece_start, _ = self._get_piece_location(piece_index)
        piece_length = self.get_piece_length(piece_index)

        if begin < 0 or length <= 0 or begin >= piece_length:
            return None

        read_length = min(length, piece_length - begin)
        range_start = piece_start + begin
        range_end = range_start + read_length

        file_spans = self._get_file_spans_for_range(range_start, range_end)
        return _read_spans_sync(file_spans)

    def get_piece_length(self, piece_index: int) -> int:
        """Return the actual length of a piece, handling the final partial piece."""
        if piece_index < 0 or piece_index >= self._total_piece_count:
            raise IndexError("piece_index out of range")

        total_length = sum(file_length for _, file_length in self.files)
        piece_start = piece_index * self._piece_length
        remaining = total_length - piece_start
        return min(self._piece_length, max(0, remaining))