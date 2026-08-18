import struct

PROTOCOL_NAME = b"BitTorrent protocol"
PROTOCOL_LENGTH = len(PROTOCOL_NAME)
HANDSHAKE_FORMAT = ">B19s8s20s20s"


def _validate_size(data: bytes, expected_size: int, name: str) -> None:
    if len(data) != expected_size:
        raise ValueError(f"invalid {name} size: expected {expected_size}, got {len(data)}")

def pack_handshake(info_hash: bytes, peer_id: bytes) -> bytes:
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

def unpack_handshake(data: bytes, expected_info_hash: bytes | None = None) -> tuple[bytes, bytes]:
    _validate_size(data, struct.calcsize(HANDSHAKE_FORMAT), "handshake")
    pstrlen, protocol_name, _reserved, info_hash, peer_id = struct.unpack(
        HANDSHAKE_FORMAT, data
    )

    if pstrlen != PROTOCOL_LENGTH or protocol_name != PROTOCOL_NAME:
        raise ValueError("invalid BitTorrent handshake from peer")
    if expected_info_hash is not None and info_hash != expected_info_hash:
        raise ValueError("peer responded with a different info_hash")
    return info_hash, peer_id 

def pack_keepalive() -> bytes:
    return struct.pack(">I", 0)

def pack_message(message_id: int, payload: bytes) -> bytes:
    return struct.pack(">IB", len(payload) + 1, message_id) + payload

def unpack_message_length_prefix(message: bytes) -> int:
    _validate_size(message, struct.calcsize(">I"), "length prefix")
    (message_length,) = struct.unpack(">I", message)
    return message_length

def pack_have_payload(piece_index: int) -> bytes:
    return struct.pack(">I", piece_index)

def unpack_have_payload(payload: bytes) -> int:
    _validate_size(payload, struct.calcsize(">I"), "have payload")
    (piece_index,) = struct.unpack(">I", payload)
    return piece_index


def pack_request_payload(piece_index: int, begin: int, length: int) -> bytes:
    return struct.pack(">III", piece_index, begin, length)

def unpack_request_payload(payload: bytes, message_name: str) -> tuple[int, int, int]:
    _validate_size(payload, struct.calcsize(">III"), f"{message_name} payload")
    return struct.unpack(">III", payload)

def pack_piece_payload(piece_index: int, begin: int, block: bytes) -> bytes:
    return struct.pack(">II", piece_index, begin) + block

def unpack_piece_payload(payload: bytes) -> tuple[int, int, bytes]:
    header_size = struct.calcsize(">II")
    if len(payload) < header_size:
        raise ValueError("invalid piece payload")
    piece_index, begin = struct.unpack(">II", payload[:header_size])
    return piece_index, begin, payload[header_size:]

def normalize_bitfield_length(payload: bytes, total_piece_count: int) -> bytes:
    expected_len = (total_piece_count + 7) // 8
    if len(payload) < expected_len:
        return payload + b"\x00" * (expected_len - len(payload))
    if len(payload) > expected_len:
        return payload[:expected_len]
    return payload

def generate_empty_bitfield(total_piece_count: int) -> bytes:
    return b"\x00" * ((total_piece_count + 7) // 8)

def set_piece_in_bitfield(bitfield: bytes | None, piece_index: int) -> bytes:
    if piece_index < 0:
        raise ValueError("piece_index must be non-negative")
    byte_index = piece_index // 8
    bit_offset = piece_index % 8
    mask = 1 << (7 - bit_offset)

    if bitfield is None:
        bitfield = b"\x00" * (byte_index + 1)
    elif byte_index >= len(bitfield):
        bitfield += b"\x00" * (byte_index - len(bitfield) + 1)

    return (
        bitfield[:byte_index]
        + bytes([bitfield[byte_index] | mask])
        + bitfield[byte_index + 1:]
    )