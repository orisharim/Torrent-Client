from peers.peers_manager import PeersManager
import random
import time
from typing import Optional
from piece import Piece
from torrent_storage import TorrentStorage
from torrent_file import TorrentFile
import asyncio
from asyncio import TaskGroup
from hashlib import sha1
from peers.peer_connection import PeerConnection
import peers.peer_protocol_encoder as protocol_encoder

class PieceManager:

    PRINT_CONNECTION_AMOUNT = True
    PRINT_PEER_PIECE_REQUESTS = False
    PRINT_DOWNLOAD_SPEED = False

    VALIDATION_INTERVAL = 30.0
    PIECE_DOWNLOAD_TIMEOUT = 120.0
    PIECE_FAILS_RETRY_DELAY = 0.5

    MAX_IN_FLIGHT_PIECES = 50
    MAX_IN_FLIGHT_PIECES_PER_PEER = 10

    def __init__( self, peer_id: bytes, peers_info: list[tuple[str, int]], torrent_metadata: TorrentFile, download_path: str) -> None:
        self._torrent_metadata = torrent_metadata
        self._peer_id = peer_id
        self._total_piece_count = len(torrent_metadata.pieces)

        self._torrent_storage = TorrentStorage(torrent_metadata, download_path)

        self._peers_manager = PeersManager(peers_info, torrent_metadata, peer_id, self._torrent_storage)

        self._requested_pieces: list[int] = []

        self._is_downloading = False
        self._is_seeding = False

        self._requested_pieces_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()

        self._validation_task: Optional[asyncio.Task] = None
        self._download_tasks: list[asyncio.Task] = []

        if PieceManager.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task: Optional[asyncio.Task] = None
        
        if PieceManager.PRINT_DOWNLOAD_SPEED:
            self._download_speed_task: Optional[asyncio.Task] = None
            self._last_downloaded_piece_amount: int = 0
            self._last_download_time: float = time.monotonic()

    async def close_all(self) -> None:
        await self.stop_downloads()
        await self._peers_manager.close_connections()
              

    async def start_downloads(self):
        """starts downloading pieces from peers if already downloading it will restart the download process."""
        await self.stop_downloads()
        await self._torrent_storage.restore_pieces_from_disk()
        await self._peers_manager.connect_to_peers()
        self._is_downloading = True
        self._validation_task = asyncio.create_task(self._validate_pieces())

        if PieceManager.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task = asyncio.create_task(self._print_connected_peers())

        if PieceManager.PRINT_DOWNLOAD_SPEED:
            self._download_speed_task = asyncio.create_task(self._print_download_speed())                


        async def download_loop():
            try:
                while True:
                    if not self._is_downloading or await self.is_complete():
                        return

                    downloaded_piece = await self._download_piece()
                    
                    if not downloaded_piece and not await self.is_complete():
                        await asyncio.sleep(self.PIECE_FAILS_RETRY_DELAY)
                    
                    if not await self.is_complete():
                        continue
                    else:
                        await self.stop_downloads()
                        return
            except Exception as e:
                if self._is_downloading:
                    print(f"Download loop error: {e}")

        self._download_tasks = []
        for _ in range(self.MAX_IN_FLIGHT_PIECES):
            self._download_tasks.append(asyncio.create_task(download_loop()))

    async def _validate_pieces(self):
        """Validates downloaded pieces and removes them if they are not valid"""
        while self._is_downloading:
            await asyncio.sleep(self.VALIDATION_INTERVAL)
            await self._torrent_storage.delete_broken_pieces()


    async def _print_connected_peers(self):
        while self._is_downloading:
            await asyncio.sleep(5.0)
            peers = await self._peers_manager.get_peers()
            connected = 0
            for peer in peers:
                if await peer.is_connected():
                    connected += 1
            print(f"Connected peers: {connected}/{len(peers)}")

    async def _print_download_speed(self):
        while self._is_downloading:
            await asyncio.sleep(1.0)
            downloaded_piece_amount = self.get_downloaded_piece_count()
            downloaded_piece_amount_difference = downloaded_piece_amount - self._last_downloaded_piece_amount
            download_time = time.monotonic() - self._last_download_time
            download_speed = downloaded_piece_amount_difference / download_time
            download_speed *=  self._torrent_metadata.piece_length / (1024 * 1024) 
            print(f"Download speed: {download_speed } megabytes/second")
            self._last_downloaded_piece_amount = downloaded_piece_amount
            self._last_download_time = time.monotonic()

    async def stop_downloads(self):
        """stops all ongoing downloads and cancels the download tasks"""
        async with self._stop_lock:
            if not self._is_downloading:
                return
            self._is_downloading = False

        if PieceManager.PRINT_CONNECTION_AMOUNT and self._print_connected_peers_task is not None:
            self._print_connected_peers_task.cancel()
            try:
                await self._print_connected_peers_task
            except asyncio.CancelledError:
                pass
            self._print_connected_peers_task = None

        if PieceManager.PRINT_DOWNLOAD_SPEED and self._download_speed_task is not None:
            self._download_speed_task.cancel()
            try:
                await self._download_speed_task
            except asyncio.CancelledError:
                pass
            self._download_speed_task = None

        # cancel the validation task
        if self._validation_task is not None:
            self._validation_task.cancel()
            try:
                await self._validation_task
            except asyncio.CancelledError:
                pass

        self._validation_task = None

        # cancel the download tasks
        current_task = asyncio.current_task()
        for task in self._download_tasks:
            if task is not current_task:
                task.cancel()
        tasks_to_await = [t for t in self._download_tasks if t is not current_task]
        if tasks_to_await:
            await asyncio.gather(*tasks_to_await, return_exceptions=True)
        self._download_tasks = []

        # send not interested to the peers
        peers_snapshot = await self._peers_manager.get_peers()

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
        await self._peers_manager.stop_seeding()
        self._is_seeding = False
    
    async def start_seeding(self):
        self._is_seeding = True
        await self._peers_manager.start_seeding()

    def is_seeding(self) -> bool:
        return self._is_seeding

    def is_downloading(self) -> bool:
        return self._is_downloading
    
    async def is_complete(self) -> bool:
        return self.get_downloaded_piece_count() == self._total_piece_count and self._torrent_storage.is_complete()
    
    def get_downloaded_piece_count(self) -> int:
        count = 0
        for i in range(self._total_piece_count):
            if protocol_encoder.check_bitfield_has_piece(self._torrent_storage.get_bitfield(), i):
                count += 1
        return count
    
    async def _download_piece(self) -> bool:
        if not self._is_downloading or await self.is_complete():
            return False

        async with self._requested_pieces_lock:
            piece_index = await self._select_next_piece()
            if piece_index is None:
                return False 
            self._requested_pieces.append(piece_index)

        peer = await self._select_peer_for_piece(piece_index)
        if peer is None:
            async with self._requested_pieces_lock:
                if piece_index in self._requested_pieces:
                    self._requested_pieces.remove(piece_index)
            return False

        if not await peer.send_piece_request(piece_index):
            async with self._requested_pieces_lock:
                if piece_index in self._requested_pieces:
                    self._requested_pieces.remove(piece_index)
            return False
            
        if PieceManager.PRINT_PEER_PIECE_REQUESTS:
            print(f"Piece {piece_index} requested from peer {peer._host}:{peer._port}")

        piece = peer.get_piece(piece_index)
        if piece is not None:
            try:
                await asyncio.wait_for(piece.wait_until_complete(), timeout=self.PIECE_DOWNLOAD_TIMEOUT)
                
                await self._torrent_storage.set_piece_in_bitfield(piece_index)
            
                async with self._requested_pieces_lock:
                    if piece_index in self._requested_pieces:
                        self._requested_pieces.remove(piece_index)
                return True
            except asyncio.TimeoutError:
                print(f"Piece {piece_index} download timeout")
                await peer.cancel_piece(piece_index)
                async with self._requested_pieces_lock:
                    if piece_index in self._requested_pieces:
                        self._requested_pieces.remove(piece_index)
                return False
        else:
            async with self._requested_pieces_lock:
                if piece_index in self._requested_pieces:
                    self._requested_pieces.remove(piece_index)
            return False

        
    async def _select_next_piece(self) -> Optional[int]:
        # get the rarest piece 
        piece_occs = [0] * self._total_piece_count
        peers_snapshot = await self._peers_manager.get_peers()

        requested_pieces_snapshot = set(self._requested_pieces)

        for peer in peers_snapshot:
            if not await peer.is_connected():
                continue

            peer_bitfield = await peer.get_bitfield()
            if peer_bitfield is None or len(peer_bitfield) == 0 or len(peer_bitfield) < (self._total_piece_count + 7) // 8:
                continue

            for piece_index in range(self._total_piece_count):  
                if protocol_encoder.check_bitfield_has_piece(self._torrent_storage.get_bitfield(), piece_index) or piece_index in requested_pieces_snapshot:
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
        peers_snapshot = await self._peers_manager.get_peers()

        peers_with_piece = []
        for peer in peers_snapshot:
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
            
    def is_piece_downloaded(self, piece_index: int) -> bool:
        return protocol_encoder.check_bitfield_has_piece(self._torrent_storage.get_bitfield(), piece_index)

