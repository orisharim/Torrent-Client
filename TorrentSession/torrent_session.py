from TorrentSession.tracker_client import TrackerClient
from TorrentSession.peers.peers import Peers
import random
import time
from typing import Optional
from TorrentSession.piece import Piece
from TorrentSession.torrent_storage import TorrentStorage
from Torrent.torrent_file import TorrentFile
import asyncio
from asyncio import TaskGroup
from hashlib import sha1
from TorrentSession.peers.peer_connection import PeerConnection
import TorrentSession.peers.peer_protocol_encoder as protocol_encoder
from torrent_settings import TorrentSettings
from TorrentSession import piece_picker

class TorrentSession:

    PRINT_CONNECTION_AMOUNT = True
    PRINT_PEER_PIECE_REQUESTS = False
    PRINT_DOWNLOAD_SPEED = False

    VALIDATION_INTERVAL = 30.0
    PIECE_DOWNLOAD_TIMEOUT = 120.0
    PIECE_FAILS_RETRY_DELAY = 0.5

    MAX_IN_FLIGHT_PIECES = 50
    MAX_IN_FLIGHT_PIECES_PER_PEER = 10

    def __init__(self, peer_id: bytes, listening_port: int, torrent_metadata: TorrentFile, torrent_storage: TorrentStorage, torrent_settings: TorrentSettings) -> None:
        self._torrent_metadata = torrent_metadata

        self._torrent_storage = torrent_storage
        self._listening_port = listening_port
        self._peer_id = peer_id
        self._torrent_settings = torrent_settings

        self._peers = Peers(peer_id, torrent_metadata, torrent_storage)
        tracker_urls = []
        if torrent_metadata.announce is not None:
            tracker_urls.append(torrent_metadata.announce.decode("utf-8"))
        for tier in torrent_metadata.announce_list:
            for tracker_url in tier:
                if tracker_url not in tracker_urls:
                    tracker_urls.append(tracker_url)

        self._tracker_urls = tracker_urls
        self._trackers: list[TrackerClient] = []
         
        self._requested_pieces: list[int] = []

        self._is_downloading = False
        self._is_seeding = False

        self._requested_pieces_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()

        self._validation_task: Optional[asyncio.Task] = None
        self._download_tasks: list[asyncio.Task] = []

        if TorrentSession.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task: Optional[asyncio.Task] = None
        
        if TorrentSession.PRINT_DOWNLOAD_SPEED:
            self._download_speed_task: Optional[asyncio.Task] = None
            self._last_downloaded_piece_amount: int = 0
            self._last_download_time: float = time.monotonic()

    async def close_all(self) -> None:
        await self.stop_downloads()
        await self.stop_seeding()
        await self._stop_trackers()
        await self._peers.close_connections()
              
    async def start_downloads(self):
        """starts downloading pieces from peers if already downloading it will restart the download process."""
        await self.stop_downloads()
        await self._torrent_storage.restore_pieces_from_disk()
        await self._start_trackers()
        await self._peers.connect_to_peers()
        self._is_downloading = True
        self._validation_task = asyncio.create_task(self._validate_pieces())

        if TorrentSession.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task = asyncio.create_task(self._print_connected_peers())

        if TorrentSession.PRINT_DOWNLOAD_SPEED:
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
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if self._is_downloading:
                    print(f"Download loop error: {e}")
                    await self.stop_downloads()

        self._download_tasks = []
        for _ in range(self.MAX_IN_FLIGHT_PIECES):
            self._download_tasks.append(asyncio.create_task(download_loop()))

    async def _start_trackers(self) -> None:
        target = self._torrent_settings.tracker_amount
        active_target = len(self._tracker_urls) if target == 0 else target

        for tracker_url in self._tracker_urls:
            if len(self._trackers) >= active_target:
                break

            tracker = TrackerClient(
                self._peers,
                tracker_url,
                self._torrent_metadata.info_hash,
                self._peer_id,
                self._listening_port,
                self._torrent_storage,
            )
            try:
                if await tracker.contact():
                    self._trackers.append(tracker)
            except Exception as exc:
                print(f"Failed to start tracker {tracker_url}: {exc}")


    async def _validate_pieces(self):
        """Validates downloaded pieces and removes them if they are not valid"""
        while True:
            if self._is_downloading:
                await self._torrent_storage.delete_broken_pieces()
            await asyncio.sleep(self.VALIDATION_INTERVAL)
            
    async def _print_connected_peers(self):
        while self._is_downloading:
            await asyncio.sleep(5.0)
            peers = await self._peers.get_peers()
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

            if TorrentSession.PRINT_CONNECTION_AMOUNT and self._print_connected_peers_task is not None:
                self._print_connected_peers_task.cancel()
                try:
                    await self._print_connected_peers_task
                except asyncio.CancelledError:
                    pass
                self._print_connected_peers_task = None

            if TorrentSession.PRINT_DOWNLOAD_SPEED and self._download_speed_task is not None:
                self._download_speed_task.cancel()
                try:
                    await self._download_speed_task
                except asyncio.CancelledError:
                    pass
                self._download_speed_task = None

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
            peers_snapshot = await self._peers.get_peers()

            announcement_tasks = []
            for connected_peer in peers_snapshot:
                if await connected_peer.is_connected():
                    announcement_tasks.append(connected_peer.send_not_interested())
            if announcement_tasks:
                async with asyncio.TaskGroup() as tg:
                    for task in announcement_tasks:
                        tg.create_task(task)

            async with self._requested_pieces_lock:
                self._requested_pieces.clear()

    async def _stop_trackers(self):
        """Stops all trackers from contacting the tracker servers"""
        await asyncio.gather(*(tracker.stop_contacting() for tracker in self._trackers))
        self._trackers.clear()

    async def stop_seeding(self):
        await self._peers.stop_seeding()
        self._is_seeding = False
    
    async def start_seeding(self):
        self._is_seeding = True
        await self._peers.start_seeding()

    def is_seeding(self) -> bool:
        return self._is_seeding

    def is_downloading(self) -> bool:
        return self._is_downloading
    
    async def is_complete(self) -> bool:
        return self._torrent_storage.is_complete()
    
    def get_downloaded_piece_count(self) -> int:
        count = 0
        for i in range(len(self._torrent_metadata.pieces)):
            if protocol_encoder.check_bitfield_has_piece(self._torrent_storage.get_bitfield(), i):
                count += 1
        return count
    
    async def _download_piece(self) -> bool:
        if not self._is_downloading or await self.is_complete():
            return False

        piece_index = await piece_picker.select_next_piece(self._torrent_storage.get_bitfield(), len(self._torrent_metadata.pieces), await self._peers.get_peers(), self._requested_pieces)
        if piece_index is None:
            return False 
            
        peer = await piece_picker.select_peer_for_piece(piece_index, await self._peers.get_peers())
        if peer is None:
            return False

        if not await peer.send_piece_request(piece_index):
            return False

        async with self._requested_pieces_lock:
            self._requested_pieces.append(piece_index)
            
        if TorrentSession.PRINT_PEER_PIECE_REQUESTS:
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
        
    
            
    def is_piece_downloaded(self, piece_index: int) -> bool:
        return protocol_encoder.check_bitfield_has_piece(self._torrent_storage.get_bitfield(), piece_index)

