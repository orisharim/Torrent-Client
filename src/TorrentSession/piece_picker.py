from random import choice
from typing import Optional
from TorrentSession.peers.peer_connection import PeerConnection
import TorrentSession.peers.peer_protocol_encoder as protocol_encoder

async def select_next_piece(bitfield: bytes, piece_count: int, peers: list[PeerConnection], requested_pieces: set[int]) -> Optional[int]:
    # get the rarest piece from connected, unchoked peers
    piece_occs = [0] * piece_count
    
    for peer in peers:
        if not await peer.is_connected() or await peer.is_choked():
            continue

        peer_bitfield = await peer.get_bitfield()
        if peer_bitfield is None or len(peer_bitfield) == 0 or len(peer_bitfield) < (piece_count + 7) // 8:
            continue

        for piece_index in range(piece_count):
            if not protocol_encoder.check_bitfield_has_piece(peer_bitfield, piece_index):
                continue
            if protocol_encoder.check_bitfield_has_piece(bitfield, piece_index) or piece_index in requested_pieces:
                continue  
            piece_occs[piece_index] += 1

    available_pieces = [index for index, occurrences in enumerate(piece_occs) if occurrences > 0]
    if not available_pieces:
        return None

    min_occs = min(piece_occs[idx] for idx in available_pieces)
    rarest_candidates = [idx for idx in available_pieces if piece_occs[idx] == min_occs]
    return choice(rarest_candidates)

async def select_peers_for_piece(piece_index: int, peers: list[PeerConnection], max_peers: int ) -> Optional[list[PeerConnection]]:
    peers_with_piece = []
    for peer in peers:
        if not await peer.is_connected():
            continue
        if peer.can_download_piece(piece_index):
            peers_with_piece.append(peer)

    if not peers_with_piece:
        return None

    peers_with_piece.sort(key=lambda p: p.get_requested_block_count())
    least_busy = peers_with_piece[0].get_requested_block_count()
    best_peers = [
        p for p in peers_with_piece
        if p.get_requested_block_count() == least_busy
    ]
    selected = []
    for peer in peers_with_piece:
        if len(selected) >= max_peers:
            break
        if peer in best_peers or len(selected) < max(1, max_peers // 2):
            selected.append(peer)
    return selected or [choice(peers_with_piece)]

