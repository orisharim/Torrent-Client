
from TorrentSession import torrent_storage
from TorrentSession.tracker_client import TrackerClient
from TorrentSession.peers.peers import Peers
from TorrentSession.session_logger import SessionLogger
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
    VALIDATION_INTERVAL = 30.0
    PIECE_DOWNLOAD_TIMEOUT = 120.0
    PIECE_FAILS_RETRY_DELAY = 0.5
    BLOCK_RETRY_DELAY = 1.0
    
    MAX_IN_FLIGHT_PIECES = 6
    MAX_PEERS_PER_IN_FLIGHT_PIECE = 5 # max amount of peers to distribute the block requests between
    DEFAULT_BLOCK_LENGTH = 16 * 1024


    def __init__(self, listening_port: int, peer_id: bytes, torrent_file_path: str, download_path: str, settings: TorrentSettings | None = None,) -> None:
        self._torrent_metadata = TorrentFile(torrent_file_path)
        self._logger = SessionLogger(self._torrent_metadata.name)
        self._logger.create_file(download_path)
        self._listening_port = listening_port
        self._torrent_storage = TorrentStorage(self._torrent_metadata, download_path, self._logger)
        self._peer_id = peer_id
        self._torrent_settings = settings or TorrentSettings()

        self._peers = Peers(peer_id, self._torrent_metadata, self._torrent_storage, self._torrent_settings, self._logger)

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
         
        self._requested_pieces: set[int] = set()

        self._is_downloading = False
        self._is_seeding = False

        self._requested_pieces_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()

        self._validation_task: Optional[asyncio.Task] = None
        self._download_tasks: list[asyncio.Task] = []

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
        self._logger.close()

    async def find_peers(self):
        await self._start_trackers()
        await self._peers.connect_to_peers()
        stats = await self._peers.get_connection_stats()
        self._logger.log_by_file("torrent_session", f"Peer discovery: {stats['known']} known, {stats['connected']} connected")
    
    async def start_downloads(self):
        """starts downloading pieces from peers if already downloading it will restart the download process."""
        await self.stop_downloads()
        await self._torrent_storage.restore_pieces_from_disk()

        if await self._peers.has_connected_peers() is False:
            await self.find_peers()    
        
        self._is_downloading = True
        self._validation_task = asyncio.create_task(self._validate_pieces())
        self._calculate_download_speed_task = asyncio.create_task(self._calculate_download_speed())                
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
                    self._logger.log_by_file("torrent_session", f"Download loop error: {e}")
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
                    self._logger,
                )
                try:
                    if not await tracker.contact():
                        continue
                except Exception as exc:
                    self._logger.log_by_file("tracker_client", f"Failed to start tracker {tracker_url}: {exc}")
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
            self._logger.log_connection_amount(
                stats["connected"],
                maximum,
                stats["connecting"],
                stats["known"],
            )

    async def _calculate_download_speed(self):
        self._last_download_time = time.monotonic()
        downloaded_pieces = await self._torrent_storage.get_downloaded_pieces()
        self._last_downloaded_piece_amount = sum(
            self._torrent_storage.get_piece_length(piece_index)
            for piece_index in downloaded_pieces
        )
        while self._is_downloading:
            await asyncio.sleep(1.0)
            downloaded_pieces = await self._torrent_storage.get_downloaded_pieces()
            downloaded_bytes = sum(
                self._torrent_storage.get_piece_length(piece_index)
                for piece_index in downloaded_pieces
            )
            now = time.monotonic()
            download_time = now - self._last_download_time
            if download_time > 0:
                downloaded_bytes_difference = downloaded_bytes - self._last_downloaded_piece_amount
                download_speed = max(0.0, downloaded_bytes_difference / download_time / (1024 * 1024))
                self._current_download_speed = download_speed
                self._logger.log_download_speed(download_speed)
                self._last_downloaded_piece_amount = downloaded_bytes
                self._last_download_time = now

        self._current_download_speed = 0.0

    async def stop_downloads(self):
        """stops all ongoing downloads and cancels the download tasks"""
        async with self._stop_lock:
            if not self._is_downloading:
                return
            self._is_downloading = False

            if self._print_connected_peers_task is not None:
                self._print_connected_peers_task.cancel()
                try:
                    await self._print_connected_peers_task
                except asyncio.CancelledError:
                    pass
                self._print_connected_peers_task = None

            if self._calculate_download_speed_task is not None:
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

        reservation = await self._reserve_next_piece()
        if reservation is None:
            return False

        piece, peers = reservation
        assigned_peers: dict[int, set[PeerConnection]] = {}
        pending_requests: dict[int, tuple[PeerConnection, float]] = {}
        peer_index = 0
        deadline = time.monotonic() + self.PIECE_DOWNLOAD_TIMEOUT

        try:
            while not piece.is_complete() and time.monotonic() < deadline:
                peer_index = await self._send_block_requests(
                    piece, peers, assigned_peers, pending_requests, peer_index
                )
                if peer_index < 0 and not pending_requests:
                    self._logger.log_by_file("torrent_session", f"No active unchoked peers left for piece {piece.index}")
                    return False

                if piece.is_complete() or time.monotonic() >= deadline:
                    break

                piece.block_received_event.clear()
                try:
                    await asyncio.wait_for(piece.block_received_event.wait(), timeout=self.BLOCK_RETRY_DELAY)
                except asyncio.TimeoutError:
                    pass

            if not piece.is_complete():
                self._logger.log_by_file("torrent_session", f"Piece {piece.index} download timed out")
                return False

            assembled_data = piece.get_assembled_data()
            if sha1(assembled_data).digest() != self._torrent_metadata.pieces[piece.index]:
                self._logger.log_by_file(
                    "torrent_session",
                    f"Piece {piece.index} failed SHA-1 validation",
                )
                return False

            await self._torrent_storage.add_piece(piece.index, None, assembled_data)
            self._logger.log_downloaded_piece(piece.index, f"piece {piece.index}")
            return True

        finally:
            await self._cancel_pending_blocks(piece.index, piece, assigned_peers)
            async with self._requested_pieces_lock:
                self._requested_pieces.discard(piece.index)

    async def _reserve_next_piece(self) -> Optional[tuple[Piece, list[PeerConnection]]]:
        async with self._requested_pieces_lock:
            available_peers = await self._peers.get_peers()
            piece_index = await piece_picker.select_next_piece(
                self._torrent_storage.get_bitfield(),
                len(self._torrent_metadata.pieces),
                available_peers,
                self._requested_pieces,
            )
            if piece_index is None:
                return None

            peers = await piece_picker.select_peers_for_piece(
                piece_index, available_peers, self.MAX_PEERS_PER_IN_FLIGHT_PIECE
            )
            if not peers:
                return None

            self._requested_pieces.add(piece_index)
            piece = Piece(
                piece_index,
                self._torrent_storage.get_piece_length(piece_index),
                self.DEFAULT_BLOCK_LENGTH,
            )
            return piece, peers

    async def _send_block_requests(
        self,
        piece: Piece,
        peers: list[PeerConnection],
        assigned_peers: dict[int, set[PeerConnection]],
        pending_requests: dict[int, tuple[PeerConnection, float]],
        peer_index: int,
    ) -> int:
        active_peers = []
        for peer in peers:
            if await peer.is_connected() and not await peer.is_choked():
                active_peers.append(peer)

        now = time.monotonic()
        REQUEST_TIMEOUT = 5.0
        expired_offsets = []
        for offset, (p, send_time) in list(pending_requests.items()):
            if piece.blocks.get(offset):
                expired_offsets.append(offset)
            elif p not in active_peers or (now - send_time > REQUEST_TIMEOUT):
                expired_offsets.append(offset)

        for offset in expired_offsets:
            pending_requests.pop(offset, None)

        if not active_peers:
            return -1

        offsets_to_request = [
            offset for offset, data in piece.blocks.items()
            if not data and offset not in pending_requests
        ]

        for offset in offsets_to_request:
            peer = active_peers[peer_index % len(active_peers)]
            peer_index += 1
            block_length = min(self.DEFAULT_BLOCK_LENGTH, piece.length - offset)
            if await peer.send_piece_request(piece.index, offset, block_length, piece):
                pending_requests[offset] = (peer, time.monotonic())
                assigned_peers.setdefault(offset, set()).add(peer)

        return peer_index

    async def _cancel_pending_blocks(self, piece_index: int, piece: Piece, assigned_peers: dict[int, set[PeerConnection]]) -> None:
        cancel_tasks = []
        for offset, peer_set in assigned_peers.items():
            block_length = min(self.DEFAULT_BLOCK_LENGTH, piece.length - offset)
            is_received = bool(piece.blocks.get(offset))
            for peer in peer_set:
                if not is_received:
                    cancel_tasks.append(peer.send_cancel_request(piece_index, offset, block_length))
                else:
                    cancel_tasks.append(peer.clear_pending_request(piece_index, offset))
        if cancel_tasks:
            await asyncio.gather(*cancel_tasks, return_exceptions=True)
                
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