import json
from pathlib import Path
from typing import Any

from src.system_logger import SystemLogger
from src.torrent_settings import GlobalTorrentSettings, TorrentSettings


STORAGE_PATH = Path(__file__).resolve().parent.parent / "storage.json"
data: dict[str, Any] = None
system_logger: SystemLogger | None = None

def _log(message: str) -> None:
    if system_logger is not None:
        system_logger.log_by_file("system_storage", message)


def open_storage(logger: SystemLogger | None = None) -> None:
    global data, system_logger
    if logger is not None:
        system_logger = logger
    if not STORAGE_PATH.exists():
        data = {}
        _log(f"Storage file does not exist; using empty storage: {STORAGE_PATH}")
        return

    try:
        with STORAGE_PATH.open("r", encoding="utf-8") as file:
            loaded_data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        _log(f"Failed to load storage file {STORAGE_PATH}: {type(exc).__name__}: {exc}")
        raise
    if not isinstance(loaded_data, dict):
        error = ValueError(f"Storage file must contain a JSON object: {STORAGE_PATH}")
        _log(str(error))
        raise error
    data = loaded_data
    _log(f"Loaded storage file: {STORAGE_PATH}")


def _ensure_data() -> dict[str, Any]:
    global data
    if data is None:
        open_storage()
    assert data is not None
    return data


def get_global_settings() -> GlobalTorrentSettings:
    settings = _ensure_data().get("global_settings", {})
    if not isinstance(settings, dict):
        raise ValueError("Stored global_settings must be a JSON object")
    return GlobalTorrentSettings(
        enable_receiving_peers=settings.get("enable_receiving_peers", True),
        enable_dht=settings.get("enable_dht", True),
        enable_port_forwarding=settings.get("enable_port_forwarding", True),
    )


def get_torrents() -> list[tuple[bytes, str, TorrentSettings]]:
    torrents = _ensure_data().get("torrents", [])
    if not isinstance(torrents, list):
        raise ValueError("Stored torrents must be a JSON array")

    result: list[tuple[bytes, str, TorrentSettings]] = []
    for torrent in torrents:
        if not isinstance(torrent, dict):
            raise ValueError("Each stored torrent must be a JSON object")
        try:
            info_hash = bytes.fromhex(torrent["info_hash"])
            download_path = torrent["download_path"]
            settings = torrent["settings"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Stored torrent has invalid fields") from exc
        if len(info_hash) != 20 or not isinstance(download_path, str) or not isinstance(settings, dict):
            raise ValueError("Stored torrent has invalid fields")

        result.append((
            info_hash,
            download_path,
            TorrentSettings(
                max_connections=settings.get("max_connections", 50),
                download_speed_limit=settings.get("download_speed_limit", 0),
                upload_speed_limit=settings.get("upload_speed_limit", 0),
                tracker_amount=settings.get("tracker_amount", 4),
            ),
        ))
    return result


def _save() -> None:
    try:
        STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with STORAGE_PATH.open("w", encoding="utf-8") as file:
            json.dump(_ensure_data(), file, indent=4)
    except (OSError, TypeError, ValueError) as exc:
        _log(f"Failed to save storage file {STORAGE_PATH}: {type(exc).__name__}: {exc}")
        raise
    _log(f"Saved storage file: {STORAGE_PATH}")


def save_global_settings(global_settings: GlobalTorrentSettings):
    _ensure_data()["global_settings"] = {
        "enable_receiving_peers": global_settings.enable_receiving_peers,
        "enable_dht": global_settings.enable_dht,
        "enable_port_forwarding": global_settings.enable_port_forwarding,
    }
    _save()


def save_torrents(torrents: list[tuple[bytes, str, TorrentSettings]]):
    serialized_torrents = []
    for info_hash, download_path, settings in torrents:
        serialized_torrents.append({
            "info_hash": info_hash.hex(),
            "download_path": download_path,
            "settings": {
                "max_connections": settings.max_connections,
                "download_speed_limit": settings.download_speed_limit,
                "upload_speed_limit": settings.upload_speed_limit,
                "tracker_amount": settings.tracker_amount
            }
        })
    _ensure_data()["torrents"] = serialized_torrents
    _save()


def add_torrent(info_hash: bytes, download_path: str, settings: TorrentSettings) -> None:
    torrents = get_torrents()
    torrents.append((info_hash, download_path, settings))
    save_torrents(torrents)