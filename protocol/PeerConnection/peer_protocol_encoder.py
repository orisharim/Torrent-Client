import struct

PROTOCOL_NAME = b"BitTorrent protocol"
PROTOCOL_LENGTH = len(PROTOCOL_NAME)
HANDSHAKE_FORMAT = ">B19s8s20s20s"
LENGTH_PREFIX_FORMAT = ">I"
MESSAGE_HEADER_FORMAT = ">IB"
HAVE_FORMAT = ">I"
BLOCK_TRIPLE_FORMAT = ">III"
PIECE_HEADER_FORMAT = ">II"


def _validate_size(data: bytes, expected_size: int, name: str) -> None:
    if len(data) != expected_size:
        raise ValueError(f"invalid {name} size: expected {expected_size}, got {len(data)}")

def encode_handshake(info_hash: bytes, peer_id: bytes) -> bytes:
    _validate_size(info_hash, 20, "info_hash")
    _validate_size(peer_id, 20, "peer_id")
    return struct.pack(
            HANDSHAKE_FORMAT,
            PROTOCOL_LENGTH,
            PROTOCOL_NAME,
            b"\x00" * 8,
            info_hash,
            peer_id,
        )

def decode_handshake(data: bytes, expected_info_hash: bytes | None = None) -> tuple[bytes, bytes]:
    _validate_size(data, struct.calcsize(HANDSHAKE_FORMAT), "handshake")
    pstrlen, protocol_name, _reserved, info_hash, peer_id = struct.unpack(
        HANDSHAKE_FORMAT, data
    )

    if pstrlen != PROTOCOL_LENGTH or protocol_name != PROTOCOL_NAME:
        raise ValueError("invalid BitTorrent handshake from peer")
    if expected_info_hash is not None and info_hash != expected_info_hash:
        raise ValueError("peer responded with a different info_hash")
    return info_hash, peer_id 


def encode_empty_message() -> bytes:
    return struct.pack(LENGTH_PREFIX_FORMAT, 0)

def encode_message(message_id: int, payload: bytes) -> bytes:
    return struct.pack(MESSAGE_HEADER_FORMAT, len(payload) + 1, message_id) + payload

def decode_length_prefix(data: bytes) -> int:
    _validate_size(data, struct.calcsize(LENGTH_PREFIX_FORMAT), "length prefix")
    (message_length,) = struct.unpack(LENGTH_PREFIX_FORMAT, data)
    return message_length

def decode_message(data: bytes) -> tuple[int, bytes]:
    if len(data) == 0:
        raise ValueError("invalid message payload")
    return data[0], data[1:]

def encode_have_payload(piece_index: int) -> bytes:
    return struct.pack(HAVE_FORMAT, piece_index)

def decode_have_payload(payload: bytes) -> int:
    _validate_size(payload, struct.calcsize(HAVE_FORMAT), "have payload")
    (piece_index,) = struct.unpack(HAVE_FORMAT, payload)
    return piece_index

def encode_block_request_payload(piece_index: int, begin: int, length: int) -> bytes:
    return struct.pack(BLOCK_TRIPLE_FORMAT, piece_index, begin, length)

def decode_block_request_payload(payload: bytes, message_name: str) -> tuple[int, int, int]:
    _validate_size(payload, struct.calcsize(BLOCK_TRIPLE_FORMAT), f"{message_name} payload")
    return struct.unpack(BLOCK_TRIPLE_FORMAT, payload)

def encode_piece_payload(piece_index: int, begin: int, block: bytes) -> bytes:
    return struct.pack(PIECE_HEADER_FORMAT, piece_index, begin) + block

def decode_piece_payload(payload: bytes) -> tuple[int, int, bytes]:
    header_size = struct.calcsize(PIECE_HEADER_FORMAT)
    if len(payload) < header_size:
        raise ValueError("invalid piece payload")
    piece_index, begin = struct.unpack(PIECE_HEADER_FORMAT, payload[:header_size])
    return piece_index, begin, payload[header_size:]

def normalize_bitfield_payload(payload: bytes, total_piece_count: int) -> bytes:
    expected_len = (total_piece_count + 7) // 8
    if len(payload) < expected_len:
        return payload + b"\x00" * (expected_len - len(payload))
    if len(payload) > expected_len:
        return payload[:expected_len]
    return payload
        


