from typing import Optional
from peer_connection import PeerConnection
from piece import Piece
from peers.peer_connection import PeerConnection

class PeerManager:
    def __init__(self, peers_info: list[tuple[str, int]], info_hash: bytes, piece_length: int) -> None:
        #get from tracker
        self.peers = list()
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, info_hash, piece_length))
        #get from torrent parser
        self.info_hash = info_hash
        self.piece_length = piece_length

        self.bitfield = bytes() #bitfield of pieces we have
        self.downloaded_pieces = set()
        self.requested_pieces = set()

    async def set_peers(self, peers_info: list[tuple[str, int]]) -> None:
        self.peers = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, self.info_hash, self.piece_length))

    async def add_peers(self, peers_info: list[tuple[str, int]]) -> None:
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, self.info_hash, self.piece_length))

    async def connect_to_peers(self) -> None:
        for peer in self.peers:
            try:
                await peer.connect()
                await peer.send_handshake()
                await peer.read_bitfield()
            except Exception as e:
                print(f"Failed to connect to peer {peer.ip}:{peer.port}: {e}")

    async def close_all(self) -> None:
        for peer in self.peers:
            await peer.close()

    async def get_piece(self) -> Optional[bytes]:
        for peer in self.peers:
            if peer.is_choked:
                continue
            # piece = await request_piece()
            if piece is not None:
                return piece
        return None
    