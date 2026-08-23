from __future__ import annotations

from typing import Optional
from PeerConnection.peer_connection import PeerConnection
from piece import Piece
from torrent_storage import TorrentStorage
from torrent import Torrent
import asyncio
from asyncio import TaskGroup
from hashlib import sha1
import PeerConnection.peer_protocol_encoder as protocol_encoder

class PieceManager:

    CONNECTION_TIMEOUT = 10.0
    RECEIVE_BITFIELD_CHECK_INTERVAL = 1.0
    RECEIVE_BITFIELD_TIMEOUT = 3.0
    RECONNECT_INTERVAL = 15.0
    VALIDATION_INTERVAL = 30.0
    PIECE_DOWNLOAD_TIMEOUT = 120.0

    MAX_IN_FLIGHT_PIECES = 20
    MAX_IN_FLIGHT_PIECES_PER_PEER = 5

    def __init__( self, peer_id: bytes, peers_info: list[tuple[str, int]], torrent_metadata: Torrent, download_path: str) -> None:
        self._torrent_metadata = torrent_metadata
        self._peer_id = peer_id
        self._total_piece_count = len(torrent_metadata.pieces)

        self._torrent_storage = TorrentStorage(torrent_metadata, download_path)

        self._peers: list[PeerConnection] = []
        for ip, port in peers_info:
            peer = PeerConnection(ip, port, torrent_metadata.info_hash, peer_id, self._torrent_storage)
            self._peers.append(peer)


        self._bitfield: bytes = protocol_encoder.generate_empty_bitfield()  
        self._requested_pieces: list[int] = []

        self._is_downloading = False
        self._is_seeding = False

        self._peers_lock = asyncio.Lock()
        self._bitfield_lock = asyncio.Lock()
        self._requested_pieces_lock = asyncio.Lock()

        self._reconnect_task: Optional[asyncio.Task] = None
        self._validation_task: Optional[asyncio.Task] = None

    async def set_peers(self, peers_info: list[tuple[str, int]]):
        await self.close_all()
        async with self._peers_lock:
            self._peers = []
            for ip, port in peers_info:
                peer = PeerConnection(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def add_peers(self, new_peers_info: list[tuple[str, int]]):
        async with self._peers_lock:
            for ip, port in new_peers_info:
                peer = PeerConnection(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def _sync_bitfield_with_storage(self) -> None:
        await self._torrent_storage.restore_pieces_from_disk()
        bitfield = protocol_encoder.generate_empty_bitfield()
        async with self._torrent_storage._downloaded_pieces_lock:
            downloaded_piece_indexes = list(self._torrent_storage._downloaded_pieces)

        for piece_index in downloaded_piece_indexes:
            bitfield = protocol_encoder.set_piece_in_bitfield(bitfield, piece_index)

        async with self._bitfield_lock:
            self._bitfield = bitfield

    async def connect_to_unconnected_peers(self) -> None:
        """Connects to any peers that are not currently connected"""
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        async with TaskGroup() as tg:
            for peer in peers_snapshot:
                if await peer.is_connected():
                    continue
                tg.create_task(peer.connect())

    async def connect_to_all_peers(self) -> None:
        """Closes all existing connections and connects to all peers"""
        await self.close_all()

        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        async with asyncio.TaskGroup() as tg:
            for peer in peers_snapshot:
                tg.create_task(peer.connect())

    async def close_all(self) -> None:
        """Closes all peer connections and cancels all ongoing downloads"""
        await self.stop_downloads()
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        for peer in peers_snapshot:
            await peer.close()       

    async def start_downloads(self):
        """starts downloading pieces from peers if already downloading it will restart the download process."""
        await self.stop_downloads()
        await self._sync_bitfield_with_storage()
        await self.connect_to_unconnected_peers()
        self._is_downloading = True
        self._reconnect_task = asyncio.create_task(self._reconnect())
        self._validation_task = asyncio.create_task(self._validate_pieces())

        peers_snapshot = []
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        
        message_loop_started = False
        for peer in peers_snapshot:
            if not await peer.is_message_loop_running():
                try:
                    await peer.connect()
                    await peer.start_message_loop()
                    message_loop_started = True
                except Exception as e:
                    print(f"Failed to start message loop for peer {peer._host}: {e}")
        
        if not message_loop_started:
            print("Failed to start message loop with any peer")
            await self.stop_downloads()
            raise ConnectionError("No peers available for downloading")
                


        async def download_loop():
            try:
                while True:
                    if not self._is_downloading or await self.is_complete():
                        return

                    await self._download_piece()
                    if (self.get_downloaded_piece_count() < self._total_piece_count) and self._is_downloading:
                        continue

                    if await self.is_complete():
                        await self.stop_downloads()
                        return
            except Exception as e:
                if self._is_downloading:
                    print(f"Download loop error: {e}")

        async with asyncio.TaskGroup() as tg:
            for _ in range(self.MAX_IN_FLIGHT_PIECES):
                tg.create_task(download_loop())

    async def _reconnect(self):
        while self._is_downloading:
            try:
                await self.connect_to_unconnected_peers()
            except Exception:
                pass
            await asyncio.sleep(self.RECONNECT_INTERVAL)

    async def _validate_pieces(self):
        while self._is_downloading:
            await asyncio.sleep(self.VALIDATION_INTERVAL)
            
            for piece_index in await self._torrent_storage.get_downloaded_pieces():
                is_valid = await self._torrent_storage._validate_piece(piece_index)
                if not is_valid:
                    await self._torrent_storage.delete_piece(piece_index)
                    async with self._bitfield_lock:
                        self._bitfield = protocol_encoder.clear_piece_in_bitfield(self._bitfield, piece_index)
                    async with self._requested_pieces_lock:
                        if piece_index in self._requested_pieces:
                            self._requested_pieces.remove(piece_index)

    async def stop_downloads(self):
        """stops all ongoing downloads and cancels the download tasks"""
        self._is_downloading = False

        # cancel the reconnect task
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        # cancel the validation task
        if self._validation_task is not None:
            self._validation_task.cancel()
            try:
                await self._validation_task
            except asyncio.CancelledError:
                pass

        self._validation_task = None
        self._reconnect_task = None

        # send not interested to the peers
        async with self._peers_lock:
            peers_snapshot = list(self._peers)

        announcement_tasks = []
        for connected_peer in peers_snapshot:
            if await connected_peer.is_connected():
                try:
                    announcement_tasks.append(connected_peer.send_not_interested())
                except Exception:
                    pass
        if announcement_tasks:
            async with asyncio.TaskGroup() as tg:
                for task in announcement_tasks:
                    tg.create_task(task)

        async with self._requested_pieces_lock:
            self._requested_pieces.clear()
        
    async def stop_seeding(self):
        self._is_seeding = False
    
    async def start_seeding(self):
        self._is_seeding = True

    def is_seeding(self) -> bool:
        return self._is_seeding

    def is_downloading(self) -> bool:
        return self._is_downloading
    
    async def is_complete(self) -> bool:
        return self.get_downloaded_piece_count() == self._total_piece_count and await self._torrent_storage.is_complete()
    
    def get_downloaded_piece_count(self) -> int:
        count = 0
        for i in range(self._total_piece_count):
            if protocol_encoder.check_bitfield_has_piece(self._bitfield, i):
                count += 1
        return count
    
    async def _download_piece(self) -> None:
        if not self._is_downloading or await self.is_complete():
            return

        piece_index = await self._select_next_piece()
        if piece_index is None:
            return 

        peer = await self._select_peer_for_piece(piece_index)
        if peer is None:
            return

        await peer.send_piece_request(piece_index)
        async with self._requested_pieces_lock:
            self._requested_pieces.append(piece_index)
        
        piece = peer.get_piece(piece_index)
        if piece is not None:
            try:
                await asyncio.wait_for(piece.wait_until_complete(), timeout=self.PIECE_DOWNLOAD_TIMEOUT)
                
                async with self._bitfield_lock:
                    self._bitfield = protocol_encoder.set_piece_in_bitfield(self._bitfield, piece_index)
            
                async with self._requested_pieces_lock:
                    if piece_index in self._requested_pieces:
                        self._requested_pieces.remove(piece_index)
            except asyncio.TimeoutError:
                print(f"Piece {piece_index} download timeout")
                async with self._requested_pieces_lock:
                    if piece_index in self._requested_pieces:
                        self._requested_pieces.remove(piece_index)

        
    async def _select_next_piece(self) -> Optional[int]:
        # get the rarest piece 
        piece_occs = [0] * self._total_piece_count
        async with self._peers_lock:
            peers_snapshot = list(self._peers)

        for peer in peers_snapshot:
            peer_bitfield = await peer.get_bitfield()
            if peer_bitfield is None or len(peer_bitfield) == 0 or len(peer_bitfield) < (self._total_piece_count + 7) // 8:
                continue

            for piece_index in range(self._total_piece_count):  
                async with self._requested_pieces_lock:
                    if protocol_encoder.check_bitfield_has_piece(self._bitfield, piece_index) or piece_index in self._requested_pieces:
                        continue  
                piece_occs[piece_index] += 1

        rarest_piece_idx = None
        min_occs = float('inf')
        for piece_index in range(self._total_piece_count):  
            if piece_occs[piece_index] > 0 and piece_occs[piece_index] < min_occs:
                min_occs = piece_occs[piece_index]
                rarest_piece_idx = piece_index

        return rarest_piece_idx

    async def _select_peer_for_piece(self, piece_index: int) -> Optional[PeerConnection]:
        async with self._peers_lock:
            peers_snapshot = list(self._peers)

        peers_with_piece = []
        for peer in peers_snapshot:
            if peer.can_download_piece(piece_index):
                peers_with_piece.append(peer)

        if not peers_with_piece:
            return None

        min_amount_requested = len(peers_with_piece[0].get_requested_pieces())
        selected_peer = peers_with_piece[0]
        for peer in peers_with_piece:
            amount_requested = len(peer.get_requested_pieces())
            if amount_requested < min_amount_requested:
                min_amount_requested = amount_requested
                selected_peer = peer

        return selected_peer
            
    def is_piece_downloaded(self, piece_index: int) -> bool:
        return protocol_encoder.check_bitfield_has_piece(self._bitfield, piece_index)

