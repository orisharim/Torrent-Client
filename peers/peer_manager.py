import random
from typing import Optional
from peers.peer_connection import PeerConnection
from peers.piece import Piece

class PeerManager:
    def __init__(
        self, peers_info: list[tuple[str, int]], info_hash: bytes, piece_length: int, total_piece_count: int) -> None:
        # get from tracker
        self.peers: list[PeerConnection] = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, info_hash))
        # get from torrent parser
        self.info_hash = info_hash
        self.piece_length = piece_length
        self.total_piece_count = total_piece_count

        self.bitfield: bytes = b""  # bitfield of pieces we have
        self.downloaded_pieces: set[int] = set()
        self.requested_pieces: set[int] = set()

    async def set_peers(self, peers_info: list[tuple[str, int]]) -> None:
        self.peers = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, self.info_hash))

    async def add_peers(self, peers_info: list[tuple[str, int]]) -> None:
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, self.info_hash))

    async def connect_to_peers(self) -> None:
        for peer in self.peers:
            try:
                await peer.connect()
                await peer.send_handshake()
                await peer.read_bitfield()
                
            except Exception as e:
                print(f"Failed to connect to peer {peer.host}:{peer.port}: {e}")

    async def close_all(self) -> None:
        for peer in self.peers:
            await peer.close()
            
    async def download_all_pieces(self) -> None:
        while True:
            next_piece = await self._get_next_piece_index()
            if next_piece is None:
                break

            piece_index, selected_peer = next_piece
            self.requested_pieces.add(piece_index)
            await self._request_piece(selected_peer, piece_index)
            self.downloaded_pieces.add(piece_index)
            self.requested_pieces.discard(piece_index)

    async def _get_piece(self) -> Optional[bytes]:
        for peer in self.peers:
            if peer.choked:
                continue
            piece = None
            # piece = await request_piece()
            if piece is not None:
                return piece
        return None
    
    async def _get_next_piece_index(self) -> Optional[tuple[int, PeerConnection]]:
        
        pieces_counts: list[tuple[int, int, list[PeerConnection]]] = []

        for idx in range(self.total_piece_count):
            if self._has_piece(self.bitfield, idx) or idx in self.requested_pieces or idx in self.downloaded_pieces:
                continue
            
            count = 0
            peers_with_piece = []
            for peer in self.peers:
                if peer.choked or not peer.bitfield:
                    continue
                if self._has_piece(peer.bitfield, idx):
                    count += 1
                    peers_with_piece.append(peer)

            if count > 0:    
                pieces_counts.append((idx, count, peers_with_piece))

        if not pieces_counts:
            return None
        
        min_count = pieces_counts[0][1] 
        for _, count, _  in pieces_counts:
            if count < min_count:
                min_count = count
                
        rarest_pieces: list[tuple[int, list[PeerConnection]]] = []
        for idx, count, peer_connection in pieces_counts:
            if min_count == count:
                rarest_pieces.append((idx, peer_connection))

        chosen_piece = random.choice(rarest_pieces)
        chosen_peer = random.choice(chosen_piece[1])
        return chosen_piece[0], chosen_peer

    # takes a bitfield and a piece idx and returns whether the bitfield indicates that the piece is there
    def _has_piece(self, bitfield: bytes, piece_index: int) -> bool:
        byte_index = piece_index // 8
        if byte_index < 0 or byte_index >= len(bitfield):
            return False

        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)
        return (bitfield[byte_index] & mask) != 0


    async def _request_piece(self, peer: PeerConnection, piece_index: int) -> Optional[bytes]:
        if peer.choked:
            return None

        # request blocks of the piece
        piece_length = self.piece_length
        blocks = []
        for begin in range(0, piece_length, PeerConnection.DEFAULT_BLOCK_LENGTH):
            block_length = min(PeerConnection.DEFAULT_BLOCK_LENGTH, piece_length - begin)
            await peer.request_block(piece_index, begin, block_length)
            block = await peer.read_block()
            blocks.append(block)

        return b"".join(blocks) 
    