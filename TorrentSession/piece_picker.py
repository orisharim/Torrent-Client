from random import choice
from typing import Optional, Sequence
from TorrentSession.peers.peer_connection import PeerConnection
import TorrentSession.peers.peer_protocol_encoder as protocol_encoder

async def select_next_piece(bitfield: bytes, piece_count: int, peers: list[PeerConnection], requested_pieces: list[int]) -> Optional[int]:
    # get the rarest piece 
    piece_occs = [0] * piece_count
    
    for peer in peers:
        if not await peer.is_connected():
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

    min_occs = piece_occs[available_pieces[0]]
    rarest_piece_idx = available_pieces[0]
    for piece_index in available_pieces:
        if piece_occs[piece_index] < min_occs:
            min_occs = piece_occs[piece_index]
            rarest_piece_idx = piece_index

    return rarest_piece_idx

async def select_peer_for_piece(piece_index: int, peers: list[PeerConnection], max_pieces_per_peer: int ) -> Optional[PeerConnection]:
    peers_with_piece = []
    for peer in peers:
        requested_piece_count = len(peer.get_requested_pieces())
        if requested_piece_count >= max_pieces_per_peer:
            continue
        if peer.can_download_piece(piece_index):
            peers_with_piece.append(peer)

    if not peers_with_piece:
        return None

    min_amount = len(peers_with_piece[0].get_requested_pieces())
    for p in peers_with_piece:
        if len(p.get_requested_pieces()) < min_amount:
            min_amount = len(p.get_requested_pieces())

    best_peers = []
    for p in peers_with_piece:
        if len(p.get_requested_pieces()) == min_amount:
            best_peers.append(p)

    return choice(best_peers)

