
import asyncio
import random
from dataclasses import dataclass
import peers_receiver
from TorrentSession.peers.peers import Peers
from port_forward import forward_port
from port_forward import delete_port
from TorrentSession.torrent_session import TorrentSession
from Torrent.torrent_file import TorrentFile
from TorrentSession.torrent_storage import TorrentStorage
import TorrentSession.tracker_client as tracker_client
from torrent_settings import TorrentSettings

LISTENING_PORT = 6881

peer_id = random.randbytes(20)


@dataclass
class TorrentState:
    torrent: TorrentFile
    storage: TorrentStorage
    settings: TorrentSettings
    session: TorrentSession


torrents: dict[str, TorrentState] = {}
gateway_service = None

async def start_torrent_client(settings: TorrentSettings | None = None):
    global gateway_service
    settings = settings or TorrentSettings()
    if settings.enable_receiving_peers:
        if not await peers_receiver.start_listening(LISTENING_PORT):
            raise RuntimeError("Could not start incoming peer listener")
    if settings.enable_port_forwarding and gateway_service is None:
        gateway_service = await forward_port(
            LISTENING_PORT,
            protocol="TCP",
            description="Torrent Client",
        )

async def add_new_torrent(torrent_file_path: str, download_path: str, settings: TorrentSettings | None = None,) -> bool:
    if torrent_file_path in torrents:
        return False

    settings = settings or TorrentSettings()
    registered = False
    try:
        torrent = TorrentFile(torrent_file_path)
        storage = TorrentStorage(torrent, download_path)
        await storage.restore_pieces_from_disk()
        session = TorrentSession(peer_id, LISTENING_PORT, torrent, storage, settings)
        if settings.enable_receiving_peers:
            await peers_receiver.register_peers(torrent.info_hash, session._peers)
            registered = True
        await session.start_downloads()
    except Exception as exc:
        print(f"Failed to add torrent {torrent_file_path}: {exc}")
        if "session" in locals():
            await session.close_all()
        if registered:
            await peers_receiver.unregister_peers(torrent.info_hash, session._peers)
        return False

    torrents[torrent_file_path] = TorrentState(
        torrent,
        storage,
        settings,
        session,
    )
    return True

async def change_torrent_session_settings(torrent_file_path: str, settings: TorrentSettings):
    state = torrents.get(torrent_file_path)
    if state is None:
        return False
    state.settings = settings
    state.session._torrent_settings = settings
    return True

async def remove_torrent(torrent_file_path: str):
    state = torrents.pop(torrent_file_path, None)
    if state is None:
        return False
    await state.session.close_all()
    if state.settings.enable_receiving_peers:
        await peers_receiver.unregister_peers(
            state.torrent.info_hash,
            state.session._peers,
        )
    return True

async def stop_torrent_client():
    for torrent_file_path in list(torrents):
        await remove_torrent(torrent_file_path)
    await peers_receiver.stop_listening()

    global gateway_service
    if gateway_service is not None:
        await delete_port(gateway_service, LISTENING_PORT)
        gateway_service = None

async def get_torrent_state(torrent_file_path: str) -> TorrentState | None:
    return torrents.get(torrent_file_path)