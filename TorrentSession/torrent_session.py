
from TorrentSession import torrent_storage
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
    PRINT_PEER_PIECE_REQUESTS = True
    PRINT_DOWNLOAD_SPEED = True

    VALIDATION_INTERVAL = 30.0
    PIECE_DOWNLOAD_TIMEOUT = 120.0
    PIECE_FAILS_RETRY_DELAY = 0.5

    MAX_IN_FLIGHT_PIECES = 100
    MAX_IN_FLIGHT_PIECES_PER_PEER = 2

    def __init__(self, listening_port: int, peer_id: bytes, torrent_file_path: str, download_path: str, settings: TorrentSettings | None = None,) -> None:
        self._torrent_metadata = TorrentFile(torrent_file_path)
        self._listening_port = listening_port
        self._torrent_storage = TorrentStorage(self._torrent_metadata, download_path)
        self._peer_id = peer_id
        self._torrent_settings = settings or TorrentSettings()

        self._peers = Peers(peer_id, self._torrent_metadata, self._torrent_storage, self._torrent_settings)

        tracker_urls = []
        if self._torrent_metadata.announce is not None:
            tracker_urls.append(self._torrent_metadata.announce.decode("utf-8"))
        for tier in self._torrent_metadata.announce_list:
            for tracker_url in tier:
                if tracker_url not in tracker_urls:
                    tracker_urls.append(tracker_url)

        self._tracker_urls = tracker_urls
        self._trackers: list[TrackerClient] = []
        self._tracker_start_tasks: list[asyncio.Task] = []
         
        self._requested_pieces: list[int] = []

        self._is_downloading = False
        self._is_seeding = False

        self._requested_pieces_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()

        self._validation_task: Optional[asyncio.Task] = None
        self._download_tasks: list[asyncio.Task] = []

        if TorrentSession.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task: Optional[asyncio.Task] = None
        
        self._calculate_download_speed_task: Optional[asyncio.Task] = None
        self._last_downloaded_piece_amount: int = 0
        self._last_download_time: float = time.monotonic()
        self._current_download_speed: float = 0.0

    async def close_all(self) -> None:
        await self.stop_downloads()
        await self.stop_seeding()
        await self._stop_trackers()
        await self._peers.close_connections()

    async def find_peers(self):
        await self._start_trackers()
        await self._peers.connect_to_peers()
        stats = await self._peers.get_connection_stats()
        print(
            f"Peer discovery: {stats['known']} known, "
            f"{stats['connected']} connected"
        )
    
    async def start_downloads(self):
        """starts downloading pieces from peers if already downloading it will restart the download process."""
        await self.stop_downloads()
        await self._torrent_storage.restore_pieces_from_disk()

        if await self._peers.has_connected_peers() is False:
            await self.find_peers()    
        
        self._is_downloading = True
        self._validation_task = asyncio.create_task(self._validate_pieces())

        self._calculate_download_speed_task = asyncio.create_task(self._calculate_download_speed())                

        if TorrentSession.PRINT_CONNECTION_AMOUNT:
            self._print_connected_peers_task = asyncio.create_task(self._print_connected_peers())

      
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
        if self._trackers or any(
            not task.done() for task in self._tracker_start_tasks
        ):
            return

        target = self._torrent_settings.tracker_amount
        if target == 0:
            active_target = len(self._tracker_urls)
        else:
            active_target = min(target, len(self._tracker_urls))

        if active_target == 0:
            return

        tracker_index = 0
        tracker_index_lock = asyncio.Lock()
        successful_trackers: list[TrackerClient] = []
        successful_trackers_lock = asyncio.Lock()
        first_success = asyncio.Event()

        async def find_tracker() -> None:
            nonlocal tracker_index

            while True:
                async with successful_trackers_lock:
                    if len(successful_trackers) >= active_target:
                        return

                async with tracker_index_lock:
                    if tracker_index >= len(self._tracker_urls):
                        return
                    tracker_url = self._tracker_urls[tracker_index]
                    tracker_index += 1

                tracker = TrackerClient(
                    self._peers,
                    tracker_url,
                    self._torrent_metadata.info_hash,
                    self._peer_id,
                    self._listening_port,
                    self._torrent_storage,
                )
                try:
                    if not await tracker.contact():
                        continue
                except Exception as exc:
                    print(f"Failed to start tracker {tracker_url}: {exc}")
                    continue

                async with successful_trackers_lock:
                    if len(successful_trackers) < active_target:
                        successful_trackers.append(tracker)
                        self._trackers.append(tracker)
                        first_success.set()
                    else:
                        await tracker.stop_contacting()

        self._tracker_start_tasks = [
            asyncio.create_task(find_tracker())
            for _ in range(active_target)
        ]
        pending = set(self._tracker_start_tasks)
        while pending and not first_success.is_set():
            _, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
            )

    async def _validate_pieces(self):
        """Validates downloaded pieces and removes them if they are not valid"""
        while True:
            if self._is_downloading:
                await self._torrent_storage.delete_broken_pieces()
            await asyncio.sleep(self.VALIDATION_INTERVAL)
            
    async def _print_connected_peers(self):
        while self._is_downloading:
            await asyncio.sleep(5.0)
            stats = await self._peers.get_connection_stats()
            maximum = stats["maximum"] or "unlimited"
            print(
                f"Peers: {stats['connected']}/{maximum} connected, "
                f"{stats['connecting']} connecting, {stats['known']} known"
            )

    async def _calculate_download_speed(self):
        while True:
            downloaded_pieces = await self._torrent_storage.get_downloaded_pieces()
            downloaded_bytes = sum(
                self._torrent_storage.get_piece_length(piece_index)
                for piece_index in downloaded_pieces
            )
            now = time.monotonic()
            download_time = now - self._last_download_time
            downloaded_bytes_difference = downloaded_bytes - self._last_downloaded_piece_amount
            download_speed = downloaded_bytes_difference / download_time / (1024 * 1024)
            self._current_download_speed = download_speed
            if TorrentSession.PRINT_DOWNLOAD_SPEED:
                print(f"Download speed: {download_speed:.2f} megabytes/second")
            self._last_downloaded_piece_amount = downloaded_bytes
            self._last_download_time = time.monotonic()
            await asyncio.sleep(1.0)
            
        self._current_download_speed = 0.0

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

            if TorrentSession.PRINT_DOWNLOAD_SPEED and self._calculate_download_speed_task is not None:
                self._calculate_download_speed_task.cancel()
                try:
                    await self._calculate_download_speed_task
                except asyncio.CancelledError:
                    pass
                self._calculate_download_speed_task = None

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

            await self._peers.close_connections()

    async def _stop_trackers(self):
        """Stops all trackers from contacting the tracker servers"""
        start_tasks = self._tracker_start_tasks
        self._tracker_start_tasks = []
        for task in start_tasks:
            if not task.done():
                task.cancel()
        if start_tasks:
            await asyncio.gather(*start_tasks, return_exceptions=True)

        trackers = self._trackers
        self._trackers = []
        if trackers:
            await asyncio.gather(
                *(tracker.stop_contacting() for tracker in trackers),
                return_exceptions=True,
            )

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

        piece_index = await piece_picker.select_next_piece(
            self._torrent_storage.get_bitfield(),
            len(self._torrent_metadata.pieces),
            await self._peers.get_peers(),
            self._requested_pieces,
        )
        if piece_index is None:
            return False

        peer = await piece_picker.select_peer_for_piece(piece_index, await self._peers.get_peers(), self.MAX_IN_FLIGHT_PIECES_PER_PEER )
        if peer is None:
            return False

        async with self._requested_pieces_lock:
            if piece_index in self._requested_pieces:
                return False
            self._requested_pieces.append(piece_index)

        if TorrentSession.PRINT_PEER_PIECE_REQUESTS:
            print(f"Requesting piece {piece_index} from {peer._host}:{peer._port}")

        if not await peer.send_piece_request(piece_index):
            async with self._requested_pieces_lock:
                if piece_index in self._requested_pieces:
                    self._requested_pieces.remove(piece_index)
            return False

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
                print(f"Piece {piece_index} download timeout from {peer._host}:{peer._port}")
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

    async def get_status(self) -> dict:
        downloaded_piece_count = self.get_downloaded_piece_count()
        total_pieces = len(self._torrent_metadata.pieces)
        connection_stats = await self._peers.get_connection_stats()
        return {
            "download_speed" : self._current_download_speed,
            "downloaded_pieces": downloaded_piece_count,
            "total_pieces": total_pieces,
            "is_downloading": self._is_downloading,
            "is_seeding": self._is_seeding,
            "connected_peers": connection_stats["connected"],
            "known_peers": connection_stats["known"],
            "connecting_peers": connection_stats["connecting"],
            "max_connections": connection_stats["maximum"],
        }

    async def change_status(self, is_downloading: Optional[bool] = None, is_seeding: Optional[bool] = None) -> None:
        if is_downloading is not None:
            if is_downloading:
                await self.start_downloads()
            else:
                await self.stop_downloads()

        if is_seeding is not None:
            if is_seeding:
                await self.start_seeding()
            else:
                await self.stop_seeding()

    async def change_settings(self, torrent_settings: TorrentSettings) -> None:
        if torrent_settings.max_connections != self._torrent_settings.max_connections:
            await self._peers.change_max_connections(torrent_settings.max_connections)
        if torrent_settings.download_speed_limit != self._torrent_settings.download_speed_limit:
            pass
        if torrent_settings.upload_speed_limit != self._torrent_settings.upload_speed_limit:
            pass
        if torrent_settings.tracker_amount != self._torrent_settings.tracker_amount:
            await self._stop_trackers()
            self._torrent_settings.tracker_amount = torrent_settings.tracker_amount
            await self._start_trackers()
        self._torrent_settings = torrent_settings
        

    def get_torrent_metadata(self) -> TorrentFile:
        return self._torrent_metadata

    def get_peers(self) -> Peers:
        return self._peers