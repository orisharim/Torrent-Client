import asyncio
from asyncio import TaskGroup
from hashlib import sha1
import random
from typing import Optional
from peers.peer_connection import PeerConnection
from peers.piece import Piece

class PeerManager:

    PIECES_AT_ONCE = 5
    CONNECTION_TIMEOUT = 10.0

    def __init__(self, peers_info: list[tuple[str, int]], info_hash: bytes, piece_length: int, total_piece_count: int, peer_id: bytes) -> None:
        self.peers: list[PeerConnection] = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, info_hash, peer_id))

        self.info_hash = info_hash
        self.piece_length = piece_length
        self.total_piece_count = total_piece_count
        self.peer_id = peer_id
        
        self.bitfield: bytes = b""  # bitfield of pieces we have
        self.downloaded_pieces: set[int] = set()
        self.requested_pieces: set[int] = set()
        
        self.paused = False

    async def set_peers(self, peers_info: list[tuple[str, int]]) -> None:
        self.peers = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, self.info_hash, self.peer_id))

    async def add_peers(self, new_peers_info: list[tuple[str, int]]) -> None:
        for ip, port in new_peers_info:
            self.peers.append(PeerConnection(ip, port, self.info_hash, self.peer_id))
    
    async def connect_to_unconnected_peers(self) -> None:        
        async with TaskGroup() as tg:
            for peer in self.peers:
                if peer.bitfield is not None: #connect to peer only if we haven't already connected to it and got its bitfield
                    continue
                tg.create_task(self._connect_to_peer(peer))
        
    async def connect_to_all_peers(self) -> None:
        await self.close_all()
        
        async with TaskGroup() as tg:
            for peer in self.peers:
                tg.create_task(self._connect_to_peer(peer))
    
    async def _connect_to_peer(self, peer: PeerConnection) -> None:
        if peer.bitfield is not None: #connect to peer only if we haven't already connected to it and got its bitfield
            return
        try:
            async with asyncio.timeout(self.CONNECTION_TIMEOUT):    
                await peer.connect()
                await peer.send_handshake()
                await peer.read_bitfield()

        except Exception as e:
            print(f"Failed to connect to peer {peer.host}:{peer.port}: {e}")
       
    async def close_all(self) -> None:
        for peer in self.peers:
            await peer.close()
            
    async def pause_downloads(self) -> None:
        self.paused = True
        for peer in self.peers:
            if peer.interested:
                await peer.send_not_interested()

    async def resume_downloads(self) -> None:
        self.paused = False
    
    async def download_pieces(self) -> None:
        if self.paused:
            return
        async with TaskGroup() as tg:
            for _ in range(self.PIECES_AT_ONCE):
                tg.create_task(self._download_piece())
            
    async def _download_piece(self) -> Optional[Piece]:
        next_piece = await self._get_next_piece_index()
        if next_piece is None:
            return None

        piece_index, selected_peer = next_piece
        self.requested_pieces.add(piece_index)
        try:
            if self.paused:
                return None

            if not selected_peer.interested:
                await selected_peer.send_interested()

            if selected_peer.choked:
                return None

            blocks: list[tuple[int, int, bytes]] = []
            for begin in range(0, self.piece_length, PeerConnection.DEFAULT_BLOCK_LENGTH):
                if self.paused:
                    await selected_peer.send_not_interested()
                    return None
                block_length = min(PeerConnection.DEFAULT_BLOCK_LENGTH, self.piece_length - begin)
                await selected_peer.request_block(piece_index, begin, block_length)
                block_index, block_begin, block = await selected_peer.read_block()
                blocks.append((block_index, block_begin, block))

            piece = Piece(blocks)
            # self.downloaded_pieces.add(piece_index)
            if(self._validate_piece(piece)):
                # self.store_piece(piece)
                pass
            return piece # TODO: store pieces to storage
        finally:
            self.requested_pieces.discard(piece_index)

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

    # takes a bitfield and a piece idx and returns whether the bitfield indicates that the piece is there(doesnt have to be our bitfield, can be a peer's bitfield)
    def _has_piece(self, bitfield: bytes, piece_index: int) -> bool:
        byte_index = piece_index // 8
        if byte_index < 0 or byte_index >= len(bitfield):
            return False

        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)
        return (bitfield[byte_index] & mask) != 0

    
    def _validate_piece(self, piece: Piece) -> bool:
        blocks = piece.get_assembled_data()
        piece_hash = sha1(blocks).digest()
        return piece_hash == self.info_hash[piece.index * self.piece_length]

    