from dataclasses import dataclass
import asyncio

from typing import List, Tuple
from typing_extensions import Optional

from torrent_settings import TorrentSettings
from Torrent.torrent_file import TorrentFile
from TorrentSession.peers.peer_connection import PeerConnection
from TorrentSession.torrent_storage import TorrentStorage


@dataclass
class PeerInfo:
    ip: str
    port: int
    failed_connection_attempts: int = 0


class Peers:
    RECONNECT_INTERVAL = 15.0

    def __init__(self, peer_id: bytes, torrent_metadata: TorrentFile, torrent_storage: TorrentStorage, torrent_settings: TorrentSettings ) -> None:
        self._connections: List[PeerConnection] = []
        self._peers_info: dict[Tuple[str, int], PeerInfo] = {}
        self._connecting_peers: set[Tuple[str, int]] = set()
        self._peers_lock = asyncio.Lock()

        self._torrent_settings = torrent_settings
        self._torrent_metadata = torrent_metadata
        self._torrent_storage = torrent_storage
        self._peer_id = peer_id
        self._is_seeding = False
        self._reconnect_task: Optional[asyncio.Task] = None

    async def _reconnect(self):
        while True:
            await asyncio.sleep(self.RECONNECT_INTERVAL)
            try:
                await self.connect_to_peers()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"Peer reconnect cycle failed: {exc}")

    async def add_peers(self, peers_info: list[tuple[str, int]]):
        async with self._peers_lock:
            for ip, port in peers_info:
                peer_key = (ip, port)
                if peer_key not in self._peers_info:
                    self._peers_info[peer_key] = PeerInfo(ip, port)

    async def add_incoming_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, remote_peer_id: bytes ) -> bool:
        peer = PeerConnection.from_connection(reader, writer, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage,)
        peer_key = (peer._host, peer._port)

        if not await self._reserve_peer(peer_key):
            print(f"Cannot accept {peer._host}:{peer._port}; ""maximum connections reached or peer is already connecting")
            return False

        connected = False
        try:
            await peer.accept_handshake(remote_peer_id)
            if not await peer.start_message_loop():
                return False
            if self._is_seeding:
                await peer.start_seeding()

            async with self._peers_lock:
                self._connections.append(peer)
            connected = True
            return True
        finally:
            async with self._peers_lock:
                self._connecting_peers.discard(peer_key)
                   
            if not connected:
                await peer.close()

    async def connect_to_peers(self):
        candidates = await self._choose_best_connection_candidates()
        tasks = []
        for peer_info in candidates:
            tasks.append(asyncio.create_task(self._connect_to_peer(peer_info)))

        if tasks:
            await asyncio.gather(*tasks)

        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def get_peers(self) -> List[PeerConnection]:
        await self._remove_closed_connections()
        async with self._peers_lock:
            return list(self._connections)

    async def _choose_best_connection_candidates(self) -> List[PeerInfo]:
        await self._remove_closed_connections()
        async with self._peers_lock:
            available_slots = len(self._peers_info)
            max_connections = self._torrent_settings.max_connections
            if max_connections > 0:
                available_slots = max_connections - len(self._connections)
                available_slots -= len(self._connecting_peers)
                available_slots = max(0, available_slots)

            candidates = []
            for peer_key, peer_info in self._peers_info.items():
                if peer_key in self._connecting_peers:
                    continue
                if self._is_peer_connected(peer_key):
                    continue
                candidates.append(peer_info)
            #select candidates with the least failed connection attempts
            candidates.sort(key=lambda peer_info: peer_info.failed_connection_attempts)
            selected = candidates[:available_slots]
            for peer_info in selected:
                self._connecting_peers.add((peer_info.ip, peer_info.port))
            return selected

    async def _connect_to_peer(self, peer_info: PeerInfo) -> bool:
        peer_key = (peer_info.ip, peer_info.port)
        peer = PeerConnection.from_address(peer_info.ip, peer_info.port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage )
        connected = False
        try:
            if not await peer.connect():
                print(f"Failed to connect to peer {peer._host}:{peer._port}")
                return False

            if not await peer.is_message_loop_running():
                if not await peer.start_message_loop():
                    print(f"Failed to start message loop for peer {peer._host}:{peer._port}")
                    return False

            async with self._peers_lock:
                self._connections.append(peer)
            connected = True
            return True
        except Exception as exc:
            print(f"Exception connecting to peer {peer._host}:{peer._port} - {exc}")
            return False
        finally:
            async with self._peers_lock:
                self._connecting_peers.discard(peer_key)
                if peer_info is not None and not connected:
                    peer_info.failed_connection_attempts += 1
            if not connected:
                await peer.close()

    async def change_max_connections(self, new_max_connections: int) -> None:
        async with self._peers_lock:
            self._torrent_settings.max_connections = new_max_connections
            if new_max_connections > 0:
                while len(self._connections) > new_max_connections:
                    peer_to_remove = self._connections.pop()
                    await peer_to_remove.close()

    async def _reserve_peer(self, peer_key: Tuple[str, int]) -> bool:
        async with self._peers_lock:
            max_connections = self._torrent_settings.max_connections
            current_connections = len(self._connections)
            reserved_connections = len(self._connecting_peers)
            if max_connections > 0 and current_connections + reserved_connections >= max_connections:
                return False
            if self._is_peer_connected(peer_key) or peer_key in self._connecting_peers:
                return False
            self._connecting_peers.add(peer_key)
            return True

    def _is_peer_connected(self, peer_key: Tuple[str, int]) -> bool:
        for peer in self._connections:
            if (peer._host, peer._port) == peer_key:
                return True
        return False

    async def _remove_closed_connections(self) -> None:
        async with self._peers_lock:
            connections = list(self._connections)

        closed_connections = []
        for peer in connections:
            if not await peer.is_connected():
                closed_connections.append(peer)

        if not closed_connections:
            return

        async with self._peers_lock:
            for peer in closed_connections:
                if peer in self._connections:
                    self._connections.remove(peer)

    async def has_connected_peers(self) -> bool:
        await self._remove_closed_connections()
        async with self._peers_lock:
            return len(self._connections) > 0

    async def close_connections(self):
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            await asyncio.gather(self._reconnect_task, return_exceptions=True)
            self._reconnect_task = None

        async with self._peers_lock:
            connections = list(self._connections)
            self._connections.clear()
            self._connecting_peers.clear()

        for peer in connections:
            await peer.close()

    async def start_seeding(self):
        self._is_seeding = True
        async with self._peers_lock:
            connections = list(self._connections)
        for peer in connections:
            await peer.start_seeding()

    async def stop_seeding(self):
        self._is_seeding = False
        async with self._peers_lock:
            connections = list(self._connections)
        for peer in connections:
            await peer.stop_seeding()
