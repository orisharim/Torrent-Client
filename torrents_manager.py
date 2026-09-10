
import asyncio
import random
from dataclasses import dataclass
from . import peers_receiver
from TorrentSession.peers.peers import Peers
from port_forward import forward_port
from port_forward import delete_port
from TorrentSession.torrent_session import TorrentSession
from Torrent.torrent_file import TorrentFile
from TorrentSession.torrent_storage import TorrentStorage
import TorrentSession.tracker_client as tracker_client

LISTENING_PORT = 6881

peer_id = random.randbytes(20)


torrents: dict[str, TorrentState] = {}
gateway_service = None

async def start_torrent_client():
    global gateway_service
    gateway_service = await forward_port(LISTENING_PORT, protocol="TCP", description="Torrent Client")

async def add_new_torrent(torrent_file_path: str, download_path: str) -> bool:
    return True

async def change_torrent_session_settings(torrent_file_path: str):
    pass

async def remove_torrent(torrent_file_path: str):
    pass

async def stop_torrent_client():
    pass
    