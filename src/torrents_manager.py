
import asyncio
import random
import shutil
from pathlib import Path

from src import peers_receiver, system_storage
from src.system_logger import SystemLogger
from src.torrent_settings import GlobalTorrentSettings, TorrentSettings
from src.TorrentSession.torrent_file import TorrentFile
from src.TorrentSession.torrent_session import TorrentSession
from src.utils.port_forward import delete_port, forward_port

LISTENING_PORT = 6881

peer_id = random.randbytes(20)
torrents: dict[tuple[bytes, str], TorrentSession] = {}
global_settings = None
gateway_service = None
system_logger = SystemLogger()
TORRENT_FILES_DIRECTORY = Path(__file__).resolve().parent.parent / "downloaded"


def _torrent_file_path(info_hash: bytes) -> Path:
    return TORRENT_FILES_DIRECTORY / f"{info_hash.hex()}.torrent"


def _copy_torrent_file(torrent_file_path: str, info_hash: bytes) -> Path:
    TORRENT_FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = _torrent_file_path(info_hash)
    source = Path(torrent_file_path).resolve()
    if source != destination.resolve():
        shutil.copy2(source, destination)
    return destination


async def _restore_torrents() -> None:
    for info_hash, download_path, settings in system_storage.get_torrents():
        torrent_file_path = _torrent_file_path(info_hash)
        if not torrent_file_path.is_file():
            system_logger.log_by_file(
                "torrents_manager",
                f"Skipping stored torrent {info_hash.hex()}: file not found at {torrent_file_path}",
            )
            continue
        try:
            await _load_torrent(str(torrent_file_path), download_path, settings)
        except Exception as exc:
            system_logger.log_by_file("torrents_manager", f"Failed to restore torrent {info_hash.hex()}: {type(exc).__name__}: {exc}")

async def start_torrent_client(settings: GlobalTorrentSettings | None = None):
    global gateway_service
    global global_settings
    system_logger.create_file()
    system_storage.open_storage(system_logger)
    global_settings = settings or system_storage.get_global_settings()
    system_storage.save_global_settings(global_settings)
    if global_settings.enable_receiving_peers:
        if not await peers_receiver.start_listening(LISTENING_PORT, system_logger):
            raise RuntimeError("Could not start incoming peer listener")
    try:
        if global_settings.enable_port_forwarding and gateway_service is None:
            gateway_service = await forward_port(LISTENING_PORT, protocol="TCP", description="Torrent Client", logger=system_logger )
    except Exception as exc:
        system_logger.log_by_file("torrents_manager", f"Failed to set up port forwarding: {exc}")
        gateway_service = None
    await _restore_torrents()

async def get_torrents() -> list[dict[str, str]]:
    return [
        {
            "info_hash": info_hash.hex(),
            "download_path": download_path,
        }
        for info_hash, download_path in torrents
    ]


async def _load_torrent(torrent_file_path: str, download_path: str, settings: TorrentSettings ) -> tuple[tuple[bytes, str], TorrentSession] | None:
    session: TorrentSession | None = None
    try:
        session = TorrentSession(LISTENING_PORT, peer_id, torrent_file_path, download_path, settings)
        info_hash = session.get_torrent_metadata().info_hash
        torrent_key = (info_hash, download_path)
        if torrent_key in torrents:
            await session.close_all()
            return None
    except Exception as exc:
        system_logger.log_by_file("torrents_manager", f"Failed to add torrent {torrent_file_path}: {exc}")
        if session is not None:
            await session.close_all()
        return None

    if global_settings.enable_receiving_peers:
        try:
            await peers_receiver.register_peers(session.get_torrent_metadata().info_hash, session.get_peers())
        except Exception as exc:
            system_logger.log_by_file("torrents_manager", f"Failed to enable receiving peers server for {torrent_file_path}: {exc}")
            await peers_receiver.unregister_peers(session.get_torrent_metadata().info_hash, session.get_peers())
            await session.close_all()
            return None

    torrents[torrent_key] = session
    return torrent_key, session


async def add_new_torrent(torrent_file_path: str, download_path: str, settings: TorrentSettings | None = None ) -> bool:
    settings = settings or TorrentSettings()

    copied_torrent_path: Path | None = None
    try:
        info_hash = TorrentFile(torrent_file_path).info_hash
        if info_hash is None:
            raise ValueError(f"Torrent file has no info hash: {torrent_file_path}")
        copied_torrent_path = _copy_torrent_file(torrent_file_path, info_hash)
    except (OSError, ValueError, TypeError) as exc:
        system_logger.log_by_file(
            "torrents_manager",
            f"Failed to copy torrent file {torrent_file_path}: {type(exc).__name__}: {exc}",
        )
        return False

    loaded_torrent = await _load_torrent(str(copied_torrent_path), download_path, settings)
    if loaded_torrent is None:
        return False

    torrent_key, session = loaded_torrent
    try:
        system_storage.add_torrent(torrent_key[0], download_path, settings)
    except (OSError, ValueError, TypeError) as exc:
        system_logger.log_by_file(
            "torrents_manager",
            f"Failed to persist torrent {torrent_file_path}: {type(exc).__name__}: {exc}",
        )
        torrents.pop(torrent_key, None)
        await session.close_all()
        if global_settings.enable_receiving_peers:
            await peers_receiver.unregister_peers(
                session.get_torrent_metadata().info_hash,
                session.get_peers(),
            )
        return False
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
    await session.change_settings(settings)
    system_storage.save_torrents([
        (stored_info_hash, stored_download_path,
            settings if (stored_info_hash, stored_download_path) == (info_hash, download_path) else stored_settings)
        for stored_info_hash, stored_download_path, stored_settings in system_storage.get_torrents()
    ])
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
            gateway_service = await forward_port(LISTENING_PORT,protocol="TCP",description="Torrent Client",logger=system_logger)
        except Exception as exc:
            system_logger.log_by_file("torrents_manager", f"Failed to set up port forwarding: {exc}")
            gateway_service = None

    elif not settings.enable_port_forwarding and global_settings.enable_port_forwarding:
        await delete_port(gateway_service, LISTENING_PORT, logger=system_logger)
        gateway_service = None

    if  settings.enable_receiving_peers and not global_settings.enable_receiving_peers:
        if not await peers_receiver.start_listening(LISTENING_PORT, system_logger):
            raise RuntimeError("Could not start incoming peer listener")

        for session in torrents.values():
            await peers_receiver.register_peers(session.get_torrent_metadata().info_hash, session.get_peers())
    elif not settings.enable_receiving_peers and global_settings.enable_receiving_peers:
        await peers_receiver.stop_listening()

    global_settings = settings
    system_storage.save_global_settings(global_settings)

async def remove_torrent(info_hash: bytes, download_path: str) -> bool:
    session = torrents.pop((info_hash, download_path), None)
    if session is None:
        return False
    await session.close_all()
    if global_settings.enable_receiving_peers:
        await peers_receiver.unregister_peers(session.get_torrent_metadata().info_hash, session.get_peers())
    
    stored_torrents = [
        stored_torrent
        for stored_torrent in system_storage.get_torrents()
        if stored_torrent[0] != info_hash or stored_torrent[1] != download_path
    ]

    system_storage.save_torrents(stored_torrents)

    if not any(stored_torrent[0] == info_hash for stored_torrent in stored_torrents):
        try:
            _torrent_file_path(info_hash).unlink(missing_ok=True)
        except OSError as exc:
            system_logger.log_by_file(
                "torrents_manager",
                f"Failed to remove stored torrent file {_torrent_file_path(info_hash)}: {type(exc).__name__}: {exc}",
            )
    return True

async def stop_torrent_client():
    for torrent_key, session in list(torrents.items()):
        await session.close_all()
        if global_settings.enable_receiving_peers:
            await peers_receiver.unregister_peers(
                session.get_torrent_metadata().info_hash,
                session.get_peers(),
            )
        torrents.pop(torrent_key, None)
    await peers_receiver.stop_listening()

    global gateway_service
    if gateway_service is not None:
        await delete_port(gateway_service, LISTENING_PORT, logger=system_logger)
        gateway_service = None
    system_logger.close()

async def get_torrent(info_hash: bytes, download_path: str) -> TorrentSession | None:
    return torrents.get((info_hash, download_path))
