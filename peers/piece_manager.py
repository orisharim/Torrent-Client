from __future__ import annotations

from typing import Optional

from peers import piece
from peers.peer_connection import PeerConnection
from peers.piece import Piece
from peers.torrent_storage import TorrentStorage

import asyncio
from asyncio import TaskGroup
from hashlib import sha1

class PieceManager:

    CONNECTION_TIMEOUT = 10.0
    RECEIVE_BITFIELD_CHECK_INTERVAL = 1.0
    BLOCK_DOWNLOAD_TIMEOUT = 10.0
    MAX_IN_FLIGHT_PIECES = 20
    MAX_IN_FLIGHT_PIECES_PER_PEER = 5
    MAX_IN_FLIGHT_BLOCKS_PER_PIECE = 6
    MAX_BLOCK_RETRIES = 3

    def __init__( self, peer_id: bytes, peers_info: list[tuple[str, int]], torrent_metadata, download_path: str) -> None:
        self._torrent_metadata = torrent_metadata
        self._peer_id = peer_id
        self._total_piece_count = len(torrent_metadata.pieces)

        self.torrent_storage = TorrentStorage(
            piece_length = torrent_metadata.piece_length,
            total_piece_count = self._total_piece_count,
            files=torrent_metadata.files,
            base_path=download_path,
        )

        self._peers: list[PeerConnection] = []
        self._pieces_requested_from_peer: dict[PeerConnection, set[int]] = {}
        for ip, port in peers_info:
            peer = PeerConnection(ip, port, torrent_metadata.info_hash, peer_id, self.torrent_storage)
            self._peers.append(peer)
            self._pieces_requested_from_peer[peer] = set()


        self._bitfield: bytes = b""  # bitfield of pieces we have
        self._requested_pieces: set[int] = set()

        self._is_downloading = False
        self._is_seeding = False

        self._peers_lock = asyncio.Lock()
        self._bitfield_lock = asyncio.Lock()
        self._requested_pieces_lock = asyncio.Lock()
        self._pieces_requested_from_peer_lock = asyncio.Lock()

        self._download_tasks: list[asyncio.Task] = []
        
    async def set_peers(self, peers_info: list[tuple[str, int]]):
        """Closes all existing connections and sets the peer list to the provided peers"""
        await self.close_all()
        async with self._peers_lock:
            self._peers = []
            self._pieces_requested_from_peer = {}
            for ip, port in peers_info:
                peer = PeerConnection(ip, port, self._torrent_metadata.info_hash, self._peer_id, self.torrent_storage)
                self._peers.append(peer)
                self._pieces_requested_from_peer[peer] = set()

    async def add_peers(self, new_peers_info: list[tuple[str, int]]):
        """Adds the provided peers to the existing peer list without closing existing connections"""
        async with self._peers_lock:
            for ip, port in new_peers_info:
                peer = PeerConnection(ip, port, self._torrent_metadata.info_hash, self._peer_id, self.torrent_storage)
                self._peers.append(peer)
                self._pieces_requested_from_peer[peer] = set()

    async def connect_to_unconnected_peers(self) -> None:
        """Connects to any peers that are not currently connected"""
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        async with TaskGroup() as tg:
            for peer in peers_snapshot:
                if await peer.is_connected():
                    continue
                tg.create_task(self._connect_to_peer(peer))

    async def connect_to_all_peers(self) -> None:
        """Closes all existing connections and connects to all peers"""
        await self.close_all()

        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        async with asyncio.TaskGroup() as tg:
            for peer in peers_snapshot:
                tg.create_task(self._connect_to_peer(peer))

    async def _connect_to_peer(self, peer: PeerConnection) -> None:
        if await peer.get_bitfield() is not None:
            return
        try:
            async with asyncio.timeout(self.CONNECTION_TIMEOUT):
                await peer.connect()
                await peer.send_handshake()
                await peer.start_message_loop()
                while (await peer.get_bitfield()) is None: # wait for bitfield
                    await asyncio.sleep(self.RECEIVE_BITFIELD_CHECK_INTERVAL)
        except asyncio.TimeoutError:
            peer.close()
        
        except Exception as e:
            print(f"Failed to connect to peer {peer.host}:{peer.port}: {e}")

    async def close_all(self) -> None:
        """Closes all peer connections and cancels all ongoing downloads"""
        await self.stop_downloads()
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        for peer in peers_snapshot:
            await peer.close()       

    async def start_downloads(self):
        """Starts downloading pieces from peers. If already downloading, it will restart the download process."""
        await self.stop_downloads()
        self._is_downloading = True
        for _ in range(self.MAX_IN_FLIGHT_PIECES):
            task = asyncio.create_task(self._download_piece())

            # make sure that if the task ended its removed
            def _remove_done_task(done_task: asyncio.Task) -> None:
                if done_task in self._download_tasks:
                    self._download_tasks.remove(done_task)
                    

            task.add_done_callback(_remove_done_task)
            self._download_tasks.append(task)

    async def stop_downloads(self):
        """Stops all ongoing downloads and cancels the download tasks"""
        self._is_downloading = False
        for task in self._download_tasks:
            task.cancel()
        if self._download_tasks:
            await asyncio.gather(*self._download_tasks, return_exceptions=True)
        self._download_tasks.clear()

        async with self._requested_pieces_lock:
            self._requested_pieces.clear()
        async with self._pieces_requested_from_peer_lock:
            for peer in self._pieces_requested_from_peer:
                self._pieces_requested_from_peer[peer].clear()
  
    async def stop_seeding(self):
        self._is_seeding = False
    
    async def start_seeding(self):
        self._is_seeding = True

    def is_seeding(self) -> bool:
        return self._is_seeding

    def is_downloading(self) -> bool:
        return self._is_downloading
    
    def is_complete(self) -> bool:
        return self.get_downloaded_piece_count() == self._total_piece_count
    
    def get_downloaded_piece_count(self) -> int:
        count = 0
        for i in range(self._total_piece_count):
            if self._check_bitfield_has_piece(self._bitfield, i):
                count += 1
        return count
    
    CHECK_FOR_AVAILABLE_PEER_INTERVAL = 1.0

    async def _download_piece(self):
        while not self.is_complete():
            if not self._is_downloading:
                return
            
            piece_index = None
            peer = None
            try:
                piece_index = await self._select_next_piece()
                if piece_index is None:
                    return

                async with self._requested_pieces_lock:    
                    self._requested_pieces.add(piece_index)

                while True:
                    peer = await self._get_peer_for_piece(piece_index)
                    if peer is None:
                        await asyncio.sleep(self.CHECK_FOR_AVAILABLE_PEER_INTERVAL)
                        if not self._is_downloading:
                            return
                        continue

                    async with self._pieces_requested_from_peer_lock:    
                        self._pieces_requested_from_peer[peer].add(piece_index)
                    
                    
                    piece = await self._download_piece_from_peer(piece_index, peer)
                    if piece is None:
                        async with self._pieces_requested_from_peer_lock:
                            self._pieces_requested_from_peer[peer].discard(piece_index)
                        continue

                    if await self._validate_piece(piece_index, piece):
                        async with self._bitfield_lock:
                            self._bitfield = self._set_piece_in_bitfield(self._bitfield, piece_index)
                        async with self._requested_pieces_lock:
                            self._requested_pieces.discard(piece_index)
                        async with self._pieces_requested_from_peer_lock:
                            self._pieces_requested_from_peer[peer].discard(piece_index)
                        await self.torrent_storage.add_piece(piece_index, piece)
                        break
                    else:
                        async with self._pieces_requested_from_peer_lock:
                            self._pieces_requested_from_peer[peer].discard(piece_index)
            finally:
                if piece_index is not None:
                    async with self._requested_pieces_lock:
                        self._requested_pieces.discard(piece_index)
                if peer is not None:
                    async with self._pieces_requested_from_peer_lock:
                        self._pieces_requested_from_peer.get(peer, set()).discard(piece_index)

    async def _select_next_piece(self) -> Optional[int]:
        while True:
            async with self._peers_lock:
                peers_snapshot = list(self._peers)
            async with self.torrent_storage._downloaded_pieces_lock:
                downloaded_pieces_snapshot = set(self.torrent_storage.downloaded_pieces.keys())
            async with self._requested_pieces_lock:
                requested_pieces_snapshot = set(self._requested_pieces)
            async with self._bitfield_lock:
                our_bitfield_snapshot = self._bitfield

            peers_bitfields: dict[PeerConnection, bytes] = {}
            for peer in peers_snapshot:
                peer_bitfield = await peer.get_bitfield()
                if peer_bitfield is not None:
                    peers_bitfields[peer] = peer_bitfield

            pieces_counts: dict[int, int] = {}
            for piece_index in range(self._total_piece_count):
                if self._check_bitfield_has_piece(our_bitfield_snapshot, piece_index):
                    continue
                if piece_index in requested_pieces_snapshot:
                    continue
                if piece_index in downloaded_pieces_snapshot:
                    continue

                count = 0
                for peer in peers_snapshot:
                    peer_bitfield = peers_bitfields.get(peer)
                    if peer_bitfield is None:
                        continue
                    if self._check_bitfield_has_piece(peer_bitfield, piece_index):
                        count += 1

                if count > 0:
                    pieces_counts[piece_index] = count

            if not pieces_counts:
                return None

            rarest_count = min(pieces_counts.values())
            rarest_pieces = [
                piece_index
                for piece_index, count in pieces_counts.items()
                if count == rarest_count
            ]

            # choose randomly among the rarest pieces
            import random
            chosen_piece = random.choice(rarest_pieces)
            async with self._requested_pieces_lock:
                if chosen_piece in self._requested_pieces:
                    continue
                return chosen_piece
            return None
            
    async def _get_peer_for_piece(self, piece_index: int) -> Optional[PeerConnection]:
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
            
        for peer in peers_snapshot:
            bitfield = await peer.get_bitfield()
            pending = self._pieces_requested_from_peer.get(peer, set())
            if (bitfield is not None and self._check_bitfield_has_piece(bitfield, piece_index) and len(pending) < self.MAX_IN_FLIGHT_PIECES_PER_PEER):
                return peer

        return None
    
    async def _download_piece_from_peer(self, piece_index: int, peer: PeerConnection) -> Optional[Piece]:
        piece_length = await self._get_piece_length(piece_index)
        piece = Piece(piece_index, piece_length)

        block_size = max(1, piece_length // self.MAX_IN_FLIGHT_BLOCKS_PER_PIECE)
        block_ranges = []
        for offset in range(0, piece_length, block_size):
            block_ranges.append((offset, min(block_size, piece_length - offset)))

        for block_offset, block_length in block_ranges:
            retries = 0
            while retries < self.MAX_BLOCK_RETRIES:
                try:
                    await peer.request_block(piece_index, block_offset, block_length)
                    block_data = await asyncio.wait_for(
                        peer.read_block(piece_index, block_offset, block_length),
                        timeout=self.BLOCK_DOWNLOAD_TIMEOUT,
                    )
                    if block_data is None:
                        raise Exception("Failed to receive block data")
                    piece.add_block(block_offset, block_data)
                    break
                except Exception as e:
                    print(f"Error downloading block {block_offset} of piece {piece_index} from peer {peer.host}:{peer.port}: {e}")
                    retries += 1
            else:
                print(f"Failed to download block {block_offset} of piece {piece_index} from peer {peer.host}:{peer.port} after {self.MAX_BLOCK_RETRIES} retries")
                return None

        return piece
    
    def _check_bitfield_has_piece(self, bitfield: bytes, piece_index: int) -> bool:
        byte_index = piece_index // 8
        if byte_index < 0 or byte_index >= len(bitfield):
            return False

        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)
        return (bitfield[byte_index] & mask) != 0
    
    def _set_piece_in_bitfield(self, bitfield: bytes, piece_index: int) -> bytes:
        byte_index = piece_index // 8
        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)

        if byte_index >= len(bitfield):
            bitfield += b'\x00' * (byte_index - len(bitfield) + 1)

        return (
            bitfield[:byte_index] +
            bytes([bitfield[byte_index] | mask]) +
            bitfield[byte_index + 1:]
        )
    
    async def _validate_piece(self, piece_index: int, piece: Piece) -> bool:
        assembled_piece = piece.get_assembled_data()
        piece_hash = sha1(assembled_piece).digest()
        if piece_index < 0 or piece_index >= self._total_piece_count:
            return False

        expected_hash = self._torrent_metadata.pieces[piece_index]
        return piece_hash == expected_hash
    
    async def _validate_all_pieces(self) -> bool:
        pass

    async def _get_piece_length(self, piece_index: int) -> int:
        default_piece_length = self._torrent_metadata.piece_length
        if piece_index < 0 or piece_index >= self._total_piece_count:
            return default_piece_length

        if piece_index < self._total_piece_count - 1:
            return default_piece_length

        total_length = self._torrent_metadata.length
        if total_length is None:
            return default_piece_length

        last_piece_length = total_length - (
            default_piece_length * (self._total_piece_count - 1)
        )
        if last_piece_length <= 0:
            return default_piece_length

        return last_piece_length

