from random import choice
from typing import Optional, Sequence

import TorrentSession.peers.peer_protocol_encoder as protocol_encoder


def select_next_piece(
    total_piece_count: int,
    peer_bitfields: Sequence[bytes],
    downloaded_bitfield: bytes,
    requested_pieces: set[int],
) -> Optional[int]:
    piece_occurrences = [0] * total_piece_count
    expected_bitfield_length = (total_piece_count + 7) // 8

    for peer_bitfield in peer_bitfields:
        if len(peer_bitfield) < expected_bitfield_length:
            continue

        for piece_index in range(total_piece_count):
            if (
                protocol_encoder.check_bitfield_has_piece(
                    downloaded_bitfield, piece_index
                )
                or piece_index in requested_pieces
            ):
                continue
            if protocol_encoder.check_bitfield_has_piece(peer_bitfield, piece_index):
                piece_occurrences[piece_index] += 1

    rarest_piece = None
    lowest_occurrences = float("inf")
    for piece_index, occurrences in enumerate(piece_occurrences):
        if occurrences > 0 and occurrences < lowest_occurrences:
            lowest_occurrences = occurrences
            rarest_piece = piece_index

    return rarest_piece


def select_peer_for_piece(peers: Sequence, piece_index: int):
    peers_with_piece = [
        peer for peer in peers if peer.can_download_piece(piece_index)
    ]
    if not peers_with_piece:
        return None

    minimum_requested = min(
        len(peer.get_requested_pieces()) for peer in peers_with_piece
    )
    least_busy_peers = [
        peer
        for peer in peers_with_piece
        if len(peer.get_requested_pieces()) == minimum_requested
    ]
    return choice(least_busy_peers)

