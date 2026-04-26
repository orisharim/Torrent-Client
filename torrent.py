import hashlib
from bencode import decode, encode


class Torrent:
    def __init__(self, path: str):
        # raw file bytes
        self._raw = self._read_file(path)

        # decoded structure (bencoded → Python)
        self.meta = self._decode()

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

    # -------------------------
    # Step 1: read file
    # -------------------------
    def _read_file(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    # -------------------------
    # Step 2: decode bencode
    # -------------------------
    def _decode(self):
        data, _ = decode(self._raw)
        return data

    # Step 3: extract fields
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

        # single-file torrent for now
        self.length = self.info.get(b'length')

    # Step 4: compute info_hash
    def _compute_info_hash(self):
        encoded_info = encode(self.info)
        self.info_hash = hashlib.sha1(encoded_info).digest()

    # Step 5: split pieces blob into list of 20-byte hashes for easier access
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
            "length": self.length,
            "info_hash": None if self.info_hash is None else self.info_hash.hex()
        }
        
t = Torrent("C:\\Users\\itays\\Downloads\\ubuntu-26.04-desktop-amd64.iso.torrent")
print(t.summary())