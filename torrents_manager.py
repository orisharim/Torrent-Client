
import asyncio
import random
from dataclasses import dataclass
from peers.peers_manager import PeersManager
from port_forward import forward_port
from port_forward import delete_port
from torrent_downloader import TorrentDownloader
from torrent_file import TorrentFile
from torrent_storage import TorrentStorage
import tracker

LISTENING_PORT = 6881
DEFAULT_CONTACTING_INTERVAL = 30

peer_id = random.randbytes(20)
@dataclass
class TorrentState:
    torrent: TorrentFile
    tracker_url: str
    downloader: TorrentDownloader
    peers_manager: PeersManager
    monitor_task: asyncio.Task | None = None
    stopped: bool = False


torrents: dict[str, TorrentState] = {}
gateway_service = None


def _downloaded_bytes(torrent: TorrentFile, downloaded_pieces: set[int]) -> int:
    return sum(torrent.get_piece_length(index) for index in downloaded_pieces)


async def _get_peers_from_trackers(
    torrent: TorrentFile,
    event: tuple[str, int],
    downloaded: int,
    uploaded: int,
    left: int,
) -> tuple[int | None, list[tuple[str, int]], str | None]:
    for tracker_url in torrent.trackers:
        interval, peers = await tracker.get_peers(
            tracker_url,
            torrent.info_hash,
            peer_id,
            LISTENING_PORT,
            event,
            downloaded,
            uploaded,
            left,
        )
        if interval is not None:
            return interval, peers, tracker_url
    return None, [], None

async def start_torrent_client():
    global gateway_service
    gateway_service = await forward_port(LISTENING_PORT, protocol="TCP", description="Torrent Client")

async def add_torrent(torrent_file_path: str, download_path: str) -> bool:
    if torrent_file_path in torrents:
        return False

    try:
        torrent = TorrentFile(torrent_file_path)
    except Exception as e:
        print(f"Error occurred while creating TorrentFile: {e}")
        return False

    torrent_storage = TorrentStorage(torrent, download_path)
    await torrent_storage.restore_pieces_from_disk()
    
    downloaded_pieces = await torrent_storage.get_downloaded_pieces()
    downloaded = _downloaded_bytes(torrent, downloaded_pieces)
    uploaded = await torrent_storage.get_uploaded_bytes()
    contacting_interval = 0
    peers = []

    print(f"Starting torrent: {torrent_file_path}")
    if torrent_storage.is_complete():
        contacting_interval, peers, tracker_url = await _get_peers_from_trackers(
            torrent, tracker.COMPLETED, downloaded, uploaded, 0
        )
    else:
        contacting_interval, peers, tracker_url = await _get_peers_from_trackers(
            torrent, tracker.STARTED, downloaded, uploaded, torrent.length-downloaded
        )

    if contacting_interval is None or tracker_url is None:
        print("Failed to get peers from tracker.")
        return False

    if contacting_interval == 0:
        contacting_interval = DEFAULT_CONTACTING_INTERVAL 
    

    peers_manager = PeersManager(peers, torrent, peer_id, torrent_storage)
    downloader = TorrentDownloader(peers_manager, torrent, torrent_storage)

    if torrent_storage.is_complete():
        await peers_manager.connect_to_peers()
        await downloader.start_seeding()
    else:
        await downloader.start_downloads()
    
    initial_contacting_interval = contacting_interval or DEFAULT_CONTACTING_INTERVAL

    async def monitor_torrent():
        try:
            interval = initial_contacting_interval
            await asyncio.sleep(interval)
            while not await downloader.is_complete():
                downloaded_pieces = await torrent_storage.get_downloaded_pieces()
                downloaded = _downloaded_bytes(torrent, downloaded_pieces)
                uploaded = await torrent_storage.get_uploaded_bytes()
                interval, peers = await tracker.get_peers(
                    state.tracker_url, torrent.info_hash, peer_id, LISTENING_PORT,
                    tracker.KEEP_ALIVE, downloaded, uploaded,
                    torrent.length-downloaded,
                )
                if interval is not None:
                    await peers_manager.update_peers(peers)
                await asyncio.sleep(interval or DEFAULT_CONTACTING_INTERVAL)

            downloaded_pieces = await torrent_storage.get_downloaded_pieces()
            downloaded = _downloaded_bytes(torrent, downloaded_pieces)
            uploaded = await torrent_storage.get_uploaded_bytes()
            interval, peers = await tracker.get_peers(
                state.tracker_url, torrent.info_hash, peer_id, LISTENING_PORT,
                tracker.COMPLETED, downloaded, uploaded, 0,
            )
            if interval is not None:
                await peers_manager.update_peers(peers)

            while not state.stopped:
                await asyncio.sleep(interval or DEFAULT_CONTACTING_INTERVAL)
                downloaded_pieces = await torrent_storage.get_downloaded_pieces()
                downloaded = _downloaded_bytes(torrent, downloaded_pieces)
                uploaded = await torrent_storage.get_uploaded_bytes()
                interval, peers = await tracker.get_peers(
                    state.tracker_url, torrent.info_hash, peer_id, LISTENING_PORT,
                    tracker.KEEP_ALIVE, downloaded, uploaded,
                    torrent.length-downloaded,
                )
                if interval is not None:
                    await peers_manager.update_peers(peers)
        except asyncio.CancelledError:
            raise
        finally:
            if torrents.get(torrent_file_path) is state:
                del torrents[torrent_file_path]

    state = TorrentState(torrent, tracker_url, downloader, peers_manager)
    state.monitor_task = asyncio.create_task(monitor_torrent())
    torrents[torrent_file_path] = state


    return True


async def stop_torrent(torrent_file_path: str):
    state = torrents.get(torrent_file_path)
    if state is None:
        return

    state.stopped = True
    current_task = asyncio.current_task()
    if state.monitor_task is not None and state.monitor_task is not current_task:
        state.monitor_task.cancel()
        await asyncio.gather(state.monitor_task, return_exceptions=True)
    await tracker.contact_tracker(
        state.tracker_url,
        state.torrent.info_hash,
        peer_id,
        LISTENING_PORT,
        tracker.STOPPED,
        0,
        0,
        0,
    )
    await state.downloader.close_all()
    if state.peers_manager._server is not None:
        await state.peers_manager.stop_listening()
    torrents.pop(torrent_file_path, None)


async def stop_torrent_client():
    for torrent_file_path in list(torrents.keys()):
        await stop_torrent(torrent_file_path)

    global gateway_service
    if gateway_service:
        await delete_port(gateway_service, LISTENING_PORT)
        gateway_service = None
    