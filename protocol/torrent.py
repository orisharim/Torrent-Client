import hashlib
from bencode import decode, encode


class Torrent:
    def __init__(self, path: str):
        # raw file bytes
        self._raw = self._read_file(path)

        # decoded structure (bencoded → Python)
        meta, _, info_bounds = decode(self._raw, capture_info=True)

        self.meta = meta
        self.info_start, self.info_end = info_bounds

        # top-level fields
        self.announce = None
        self.info = None

        # extracted metadata
        self.piece_length = None
        self.pieces_blob = None
        self.pieces = []          # list of 20-byte hashes
        self.length = None

        # critical field
        self.info_hash = None

        # run parsing pipeline
        self._parse()

    def _read_file(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    # decode bencode
    def _decode(self):
        data, _ = decode(self._raw)
        return data

    # extract fields
    def _parse(self):
        self._extract_main_fields()
        self._extract_info_fields()
        self._compute_info_hash()
        self._split_pieces()

    def _extract_main_fields(self):
        self.announce = self.meta[b'announce']
        self.info = self.meta[b'info']

    def _extract_info_fields(self):
        self.piece_length = self.info[b'piece length']
        self.pieces_blob = self.info[b'pieces']

        # Check for multi-file torrent
        if b'files' in self.info:
            self.files = self.info[b'files']
            self.files_info = []
            for file in self.files:
                path_parts = [p.decode('utf-8', errors='ignore') for p in file[b'path']]
                self.files_info.append((path_parts, file[b'length']))
            self.length = sum(file[1] for file in self.files_info)
        else:
            # in case of single-file torrent
            self.length = self.info.get(b'length')
            self.files = None
            if self.length:
                name_bytes = self.info.get(b'name')
                name_str = name_bytes.decode('utf-8', errors='ignore') if isinstance(name_bytes, bytes) else str(name_bytes)
                self.files_info = [([name_str], self.length)]
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

    # Debug helper
    def summary(self):
        return {
            "announce": self.announce,
            "piece_length": self.piece_length,
            "num_pieces": len(self.pieces),
            "files_info": self.files_info,
            "info_hash": None if self.info_hash is None else self.info_hash.hex()
        }