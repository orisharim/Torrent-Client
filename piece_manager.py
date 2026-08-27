
import time
from typing import Optional
from peer_connection import PeerConnection
from piece import Piece
from torrent_storage import TorrentStorage
from torrent import Torrent
import asyncio
from asyncio import TaskGroup
from hashlib import sha1
import peer_protocol_encoder as protocol_encoder

class PieceManager:

    PRINT_CONNECTION_AMOUNT = False
    PRINT_PEER_PIECE_REQUESTS = False
    PRINT_DONWLOAD_SPEED = True

    CONNECTION_TIMEOUT = 10.0
    RECEIVE_BITFIELD_CHECK_INTERVAL = 1.0
    RECEIVE_BITFIELD_TIMEOUT = 3.0
    RECONNECT_INTERVAL = 15.0
    VALIDATION_INTERVAL = 30.0
    PIECE_DOWNLOAD_TIMEOUT = 120.0

    MAX_IN_FLIGHT_PIECES = 50
    MAX_IN_FLIGHT_PIECES_PER_PEER = 10

    def __init__( self, peer_id: bytes, peers_info: list[tuple[str, int]], torrent_metadata: Torrent, download_path: str) -> None:
        self._torrent_metadata = torrent_metadata
        self._peer_id = peer_id
        self._total_piece_count = len(torrent_metadata.pieces)

        self._torrent_storage = TorrentStorage(torrent_metadata, download_path)

        self._peers: list[PeerConnection] = []
        for ip, port in peers_info:
            peer = PeerConnection(ip, port, torrent_metadata.info_hash, peer_id, self._torrent_storage)
            self._peers.append(peer)

        self._requested_pieces: list[int] = []

        self._is_downloading = False
        self._is_seeding = False

        self._peers_lock = asyncio.Lock()
        self._requested_pieces_lock = asyncio.Lock()

        self._reconnect_task: Optional[asyncio.Task] = None
        self._validation_task: Optional[asyncio.Task] = None
        self._download_tasks: list[asyncio.Task] = []

        if PieceManager.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task: Optional[asyncio.Task] = None
        
        if PieceManager.PRINT_DONWLOAD_SPEED:
            self._download_speed_task: Optional[asyncio.Task] = None
            self._last_downloaded_piece_amount: int = 0
            self._last_download_time: float = time.monotonic()



    async def set_peers(self, peers_info: list[tuple[str, int]]):
        """Closes all peer connections and sets the list of peers"""
        await self.close_all()
        async with self._peers_lock:
            self._peers = []
            for ip, port in peers_info:
                peer = PeerConnection(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def add_peers(self, new_peers_info: list[tuple[str, int]]):
        """Adds new peers to the list of peers"""
        async with self._peers_lock:
            for ip, port in new_peers_info:
                peer = PeerConnection(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def _sync_bitfield_with_storage(self) -> None:
        """Restores the bitfield from disk and updates it with downloaded pieces"""
        await self._torrent_storage.restore_pieces_from_disk()
        async with self._torrent_storage._bitfield_lock:
            bitfield = protocol_encoder.generate_empty_bitfield(self._total_piece_count)
            async with self._torrent_storage._downloaded_pieces_lock:
                downloaded_piece_indexes = list(self._torrent_storage._downloaded_pieces)

            for piece_index in downloaded_piece_indexes:
                bitfield = protocol_encoder.set_piece_in_bitfield(bitfield, piece_index)

            self._torrent_storage._bitfield = bitfield

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

    async def _connect_to_peer(self, peer: PeerConnection) -> bool:
        try:
            success = await peer.connect()
            if not success:
                print(f"Failed to connect to peer {peer._host}:{peer._port}")
                return False

            return True
        except Exception as e:
            print(f"Exception connecting to peer {peer._host}:{peer._port} - {e}")
            return False

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

        if PieceManager.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task = asyncio.create_task(self._print_connected_peers())

        if PieceManager.PRINT_DONWLOAD_SPEED:
            self._download_speed_task = asyncio.create_task(self._print_download_speed())

        peers_snapshot = []
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        
        message_loop_started = False
        for peer in peers_snapshot:
            if await peer.is_message_loop_running():
                message_loop_started = True
                break
        
        if not message_loop_started:
            print("Failed to start message loop with any peer")
            await self.stop_downloads()
            raise ConnectionError("No peers available for downloading")
                


        async def download_loop():
            try:
                while True:
                    if not self._is_downloading or await self.is_complete():
                        return

                    downloaded = await self._download_piece()
                    if not downloaded:
                        await asyncio.sleep(1.0)
                    if (self.get_downloaded_piece_count() < self._total_piece_count) and self._is_downloading:
                        continue

                    if await self.is_complete():
                        await self.stop_downloads()
                        return
            except Exception as e:
                if self._is_downloading:
                    print(f"Download loop error: {e}")

        self._download_tasks = []
        for _ in range(self.MAX_IN_FLIGHT_PIECES):
            self._download_tasks.append(asyncio.create_task(download_loop()))

    async def _reconnect(self):
        while self._is_downloading:
            try:
                await self.connect_to_unconnected_peers()
            except Exception:
                pass
            await asyncio.sleep(self.RECONNECT_INTERVAL)

    async def _validate_pieces(self):
        """Validates downloaded pieces and removes them if they are not valid"""
        while self._is_downloading:
            await asyncio.sleep(self.VALIDATION_INTERVAL)
            
            for piece_index in await self._torrent_storage.get_downloaded_pieces():
                is_valid = await self._torrent_storage._validate_piece(piece_index)
                if not is_valid:
                    await self._torrent_storage.delete_piece(piece_index)
                    await self._torrent_storage.clear_piece_in_bitfield(piece_index)
                    async with self._requested_pieces_lock:
                        if piece_index in self._requested_pieces:
                            self._requested_pieces.remove(piece_index)

    async def _print_connected_peers(self):
        while True:
            await asyncio.sleep(5.0)
            async with self._peers_lock:
                connected_peers = [peer for peer in self._peers if await peer.is_connected()]
                print(f"Connected peers: {len(connected_peers)}/{len(self._peers)}")

    async def _print_download_speed(self):
        while self._is_downloading:
            await asyncio.sleep(1.0)
            downloaded_piece_amount = self.get_downloaded_piece_count()
            downloaded_piece_amount_difference = downloaded_piece_amount - self._last_downloaded_piece_amount
            download_time = time.monotonic() - self._last_download_time
            download_speed = downloaded_piece_amount_difference / download_time
            print(f"Download speed: {download_speed} pieces/second")
            self._last_downloaded_piece_amount = downloaded_piece_amount
            self._last_download_time = time.monotonic()

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
        async with self._peers_lock:
            peers_snapshot = list(self._peers)

        requested_pieces_snapshot = set(self._requested_pieces)

        for peer in peers_snapshot:
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
        async with self._peers_lock:
            peers_snapshot = list(self._peers)

        peers_with_piece = []
        for peer in peers_snapshot:
            if peer.can_download_piece(piece_index):
                peers_with_piece.append(peer)

        if not peers_with_piece:
            return None

        # Find the minimum amount requested among all eligible peers
        min_amount = min(len(p.get_requested_pieces()) for p in peers_with_piece)

        # Filter all peers that have this minimum amount requested
        best_peers = [p for p in peers_with_piece if len(p.get_requested_pieces()) == min_amount]

        # Randomly choose one of the best peers to distribute the load
        import random
        return random.choice(best_peers)
            
    def is_piece_downloaded(self, piece_index: int) -> bool:
        return protocol_encoder.check_bitfield_has_piece(self._torrent_storage.get_bitfield(), piece_index)

