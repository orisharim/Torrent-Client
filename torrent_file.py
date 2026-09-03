import hashlib
from typing import List, Tuple, Dict, Any, Optional
from bencode import decode_bencode

class TorrentFile:
    def __init__(self, path: str):
        # raw file bytes
        self._raw = self._read_file(path)

        # decoded structure (bencoded to python)
        meta, _, info_bounds = decode_bencode(self._raw, capture_info=True)

        self.meta = meta
        self.info_start, self.info_end = info_bounds

        # toplevel fields
        self.announce: Optional[bytes] = None
        self.announce_list: List[List[str]] = []
        self.info: Dict[bytes, Any] = {}

        # extracted metadata
        self.name: Optional[str] = None
        self.comment: Optional[str] = None
        self.created_by: Optional[str] = None
        self.creation_date: Optional[int] = None
        self.encoding: Optional[str] = None

        self.piece_length: Optional[int] = None
        self.pieces_blob: Optional[bytes] = None
        self.pieces: List[bytes] = []          # list of 20-byte hashes
        self.length: Optional[int] = None
        self.files: Optional[List[Dict[bytes, Any]]] = None
        self.files_info: List[Tuple[List[str], int]] = []      # list of (path_parts, length) tuples

        # torrent flags
        self.is_private: bool = False
        self.is_multi_file: bool = False

        # web seeds (just url list)
        self.web_seeds: List[str] = []

        self.info_hash: Optional[bytes] = None

        self._parse()

    def _read_file(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def _decode(self):
        data, _, _ = decode_bencode(self._raw)
        return data

    # extract fields
    def _parse(self):
        self._extract_main_fields()
        self._extract_info_fields()
        self._compute_info_hash()
        self._split_pieces()

    def _extract_main_fields(self):
        # announce (primary tracker)
        if b'announce' in self.meta:
            self.announce = self.meta[b'announce']

        # announce-list (multi-tracker extension, BEP 0012)
        if b'announce-list' in self.meta and isinstance(self.meta[b'announce-list'], list):
            self.announce_list = []
            for tier in self.meta[b'announce-list']:
                if isinstance(tier, list):
                    tier_urls = []
                    for url in tier:
                        url_str = url.decode('utf-8', errors='ignore') if isinstance(url, bytes) else str(url)
                        tier_urls.append(url_str)
                    if tier_urls:
                        self.announce_list.append(tier_urls)

        # url-list (web seeds extension, BEP 0019)
        if b'url-list' in self.meta:
            url_list = self.meta[b'url-list']
            if isinstance(url_list, bytes):
                self.web_seeds.append(url_list.decode('utf-8', errors='ignore'))
            elif isinstance(url_list, list):
                for url in url_list:
                    if isinstance(url, bytes):
                        self.web_seeds.append(url.decode('utf-8', errors='ignore'))

        # comment
        if b'comment' in self.meta:
            c = self.meta[b'comment']
            self.comment = c.decode('utf-8', errors='ignore') if isinstance(c, bytes) else str(c)

        # created by
        if b'created by' in self.meta:
            cb = self.meta[b'created by']
            self.created_by = cb.decode('utf-8', errors='ignore') if isinstance(cb, bytes) else str(cb)

        # creation date
        if b'creation date' in self.meta:
            self.creation_date = self.meta[b'creation date']

        # encoding
        if b'encoding' in self.meta:
            enc = self.meta[b'encoding']
            self.encoding = enc.decode('utf-8', errors='ignore') if isinstance(enc, bytes) else str(enc)

        self.info = self.meta[b'info']

    def _extract_info_fields(self):
        self.piece_length = self.info[b'piece length']
        self.pieces_blob = self.info[b'pieces']

        # Name / UTF-8 Name
        if b'name.utf-8' in self.info:
            n = self.info[b'name.utf-8']
            self.name = n.decode('utf-8', errors='ignore') if isinstance(n, bytes) else str(n)
        elif b'name' in self.info:
            n = self.info[b'name']
            self.name = n.decode('utf-8', errors='ignore') if isinstance(n, bytes) else str(n)

        # Private torrent flag (BEP 0027)
        self.is_private = bool(self.info.get(b'private', 0) == 1)

        # Check for multi-file torrent
        if b'files' in self.info:
            self.is_multi_file = True
            self.files = self.info[b'files']
            self.files_info = []

            for file_dict in self.files:
                length = file_dict[b'length']

                # Check path.utf-8 first (BEP 0047), fallback to path
                if b'path.utf-8' in file_dict:
                    raw_path = file_dict[b'path.utf-8']
                else:
                    raw_path = file_dict[b'path']

                path_parts = [p.decode('utf-8', errors='ignore') if isinstance(p, bytes) else str(p) for p in raw_path]
                self.files_info.append((path_parts, length))

            self.length = sum(file[1] for file in self.files_info)
        else:
            self.is_multi_file = False
            self.length = self.info.get(b'length', 0)
            self.files = None
            if self.name and self.length:
                self.files_info = [([self.name], self.length)]
            else:
                self.files_info = []

    def _compute_info_hash(self):
        info_bytes = self._raw[self.info_start:self.info_end]
        self.info_hash = hashlib.sha1(info_bytes).digest()

    # split pieces blob into list of 20-byte hashes for easier access
    def _split_pieces(self):
        blob = self.pieces_blob
        self.pieces = [
            blob[i:i+20]
            for i in range(0, len(blob), 20)
        ]

    # Property to get all trackers (announce + announce-list) deduplicated in order
    @property
    def trackers(self) -> List[str]:
        seen = set()
        trackers_list = []

        if self.announce:
            announce_str = self.announce.decode('utf-8', errors='ignore') if isinstance(self.announce, bytes) else str(self.announce)
            if announce_str and announce_str not in seen:
                seen.add(announce_str)
                trackers_list.append(announce_str)

        for tier in self.announce_list:
            for url in tier:
                if url not in seen:
                    seen.add(url)
                    trackers_list.append(url)

        return trackers_list

    @property
    def num_pieces(self) -> int:
        return len(self.pieces)

    @property
    def info_hash_hex(self) -> str:
        return self.info_hash.hex() if self.info_hash else ""

    @property
    def last_piece_length(self) -> int:
        if not self.length or not self.piece_length:
            return 0
        remainder = self.length % self.piece_length
        return remainder if remainder != 0 else self.piece_length

    def get_piece_length(self, piece_index: int) -> int:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range (0-{self.num_pieces - 1})")
        if piece_index == self.num_pieces - 1:
            return self.last_piece_length
        return self.piece_length

    def get_piece_offset(self, piece_index: int) -> int:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range (0-{self.num_pieces - 1})")
        return piece_index * self.piece_length

    def verify_piece(self, piece_index: int, piece_data: bytes) -> bool:
        if piece_index < 0 or piece_index >= self.num_pieces:
            return False
        expected_hash = self.pieces[piece_index]
        actual_hash = hashlib.sha1(piece_data).digest()
        return actual_hash == expected_hash

    # Debug helper
    def summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "announce": self.announce,
            "trackers": self.trackers,
            "web_seeds": self.web_seeds,
            "piece_length": self.piece_length,
            "num_pieces": self.num_pieces,
            "length": self.length,
            "is_private": self.is_private,
            "is_multi_file": self.is_multi_file,
            "files_info": self.files_info,
            "info_hash": None if self.info_hash is None else self.info_hash_hex,
            "comment": self.comment,
            "created_by": self.created_by,
            "creation_date": self.creation_date,
        }
