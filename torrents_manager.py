
import asyncio
import random
import peers_receiver
from TorrentSession.peers.peers import Peers
from port_forward import forward_port
from port_forward import delete_port
from TorrentSession.torrent_session import TorrentSession
from Torrent.torrent_file import TorrentFile
from TorrentSession.torrent_storage import TorrentStorage
from torrent_settings import GlobalTorrentSettings, TorrentSettings

LISTENING_PORT = 6881
TorrentKey = tuple[bytes, str]

peer_id = random.randbytes(20)
torrents: dict[TorrentKey, TorrentSession] = {}
global_settings = None
gateway_service = None

async def start_torrent_client(settings: GlobalTorrentSettings | None = None):
    global gateway_service
    global global_settings
    global_settings = settings or GlobalTorrentSettings()

    if global_settings.enable_receiving_peers:
        if not await peers_receiver.start_listening(LISTENING_PORT):
            raise RuntimeError("Could not start incoming peer listener")
    try:
        if global_settings.enable_port_forwarding and gateway_service is None:
            gateway_service = await forward_port(
                LISTENING_PORT,
                protocol="TCP",
                description="Torrent Client",
            )
    except Exception as exc:
        print(f"Failed to set up port forwarding: {exc}")
        gateway_service = None

async def get_torrents() -> list[dict[str, str]]:
    return [
        {
            "info_hash": info_hash.hex(),
            "download_path": download_path,
        }
        for info_hash, download_path in torrents
    ]


async def add_new_torrent(torrent_file_path: str, download_path: str, settings: TorrentSettings | None = None,) -> bool:
    settings = settings or TorrentSettings()

    session : TorrentSession = None
    try:
        session = TorrentSession(peer_id, torrent_file_path, download_path, settings)
        info_hash = session.get_torrent_metadata().info_hash
        torrent_key = (info_hash, download_path)
        if torrent_key in torrents:
            await session.close_all()
            return False
        await session.find_peers()
    except Exception as exc:
        print(f"Failed to add torrent {torrent_file_path}: {exc}")
        if session is not None:
            await session.close_all()
        return False

    if global_settings.enable_receiving_peers:
        try:
            await peers_receiver.register_peers(session.get_torrent_metadata().info_hash, session.get_peers())
        except Exception as exc:
            print(f"Failed to enable receiving peers server for {torrent_file_path}: {exc}")
            await peers_receiver.unregister_peers(session.get_torrent_metadata().info_hash, session.get_peers())
            return False

    torrents[torrent_key] = session
    return True

async def get_torrent_settings(info_hash: bytes, download_path: str) -> TorrentSettings | None:
    session = torrents.get((info_hash, download_path))
    if session is None:
        return None
    return session.get_settings()

async def change_torrent_settings(info_hash: bytes, download_path: str, settings: TorrentSettings) -> bool:
    session = torrents.get((info_hash, download_path))
    if session is None:
        return False
    session.change_settings(settings)
    return True

async def get_torrent_status(info_hash: bytes, download_path: str) -> dict | None:
    session = torrents.get((info_hash, download_path))
    if session is None:
        return None
    return await session.get_status()

async def change_torrent_status(info_hash: bytes, download_path: str, is_downloading: bool, is_seeding: bool) -> bool:
    session = torrents.get((info_hash, download_path))
    if session is None:
        return False

    await session.change_status(is_downloading, is_seeding)

    return True

async def change_global_settings(settings: GlobalTorrentSettings) -> None:
    global global_settings, gateway_service
    
    if settings.enable_port_forwarding and not global_settings.enable_port_forwarding:
        try:
            gateway_service = await forward_port(
                LISTENING_PORT,
                protocol="TCP",
                description="Torrent Client",
            )
        except Exception as exc:
            print(f"Failed to set up port forwarding: {exc}")
            gateway_service = None

    elif not settings.enable_port_forwarding and global_settings.enable_port_forwarding:
        await delete_port(gateway_service, LISTENING_PORT)
        gateway_service = None

    if  settings.enable_receiving_peers and not global_settings.enable_receiving_peers:
        if not await peers_receiver.start_listening(LISTENING_PORT):
            raise RuntimeError("Could not start incoming peer listener")

        for session in torrents.values():
            await peers_receiver.register_peers(session.get_torrent_metadata().info_hash, session.get_peers())
    elif not settings.enable_receiving_peers and global_settings.enable_receiving_peers:
        await peers_receiver.stop_listening()

    global_settings = settings

async def remove_torrent(info_hash: bytes, download_path: str) -> bool:
    session = torrents.pop((info_hash, download_path), None)
    if session is None:
        return False
    await session.close_all()
    if global_settings.enable_receiving_peers:
        await peers_receiver.unregister_peers(session.get_torrent_metadata().info_hash, session.get_peers())
    return True

async def stop_torrent_client():
    for info_hash, download_path in list(torrents):
        await remove_torrent(info_hash, download_path)
    await peers_receiver.stop_listening()

    global gateway_service
    if gateway_service is not None:
        await delete_port(gateway_service, LISTENING_PORT)
        gateway_service = None

async def get_torrent(info_hash: bytes, download_path: str) -> TorrentSession | None:
    return torrents.get((info_hash, download_path))

