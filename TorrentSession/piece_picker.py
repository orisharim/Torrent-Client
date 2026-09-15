from random import choice, random
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
            if protocol_encoder.check_bitfield_has_piece(bitfield, piece_index) or piece_index in requested_pieces:
                continue  
            piece_occs[piece_index] += 1

    min_occs = piece_occs[0]
    rarest_piece_idx = 0
    for piece_index in range(piece_count):  
        if piece_occs[piece_index] > 0 and piece_occs[piece_index] < min_occs:
            min_occs = piece_occs[piece_index]
            rarest_piece_idx = piece_index

    return rarest_piece_idx

async def select_peer_for_piece(piece_index: int, peers: list[PeerConnection]) -> Optional[PeerConnection]:
    peers_with_piece = []
    for peer in peers:
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

    return random.choice(best_peers)

