from typing_extensions import Optional
from TorrentSession.torrent_storage import TorrentStorage
from TorrentSession.peers.peer_connection import PeerConnection
from typing import List, Tuple
from Torrent.torrent_file import TorrentFile
import asyncio

class Peers:
    
    RECONNECT_INTERVAL: float = 15.0
    
    def __init__(self, peer_id: bytes, torrent_metadata: TorrentFile, torrent_storage: TorrentStorage) -> None:
        self._peers: List[PeerConnection] = []
        self._peers_lock: asyncio.Lock = asyncio.Lock() 
        self._peers_info: list[tuple[str, int]] = []

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

    async def set_peers(self, peers_info: list[tuple[str, int]]):
        """Closes all peer connections and sets the list of peers"""
        await self.close_connections()
        self._peers_info = peers_info
        async with self._peers_lock:
            self._peers = []
            for ip, port in peers_info:
                peer = PeerConnection.from_address(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def add_peers(self, peers_info: list[tuple[str, int]]):
        """Adds only tje new peers to the list of peers"""
        async with self._peers_lock:
            for ip, port in peers_info:
                if (ip, port) not in self._peers_info:
                    peer = PeerConnection.from_address(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                    self._peers_info.append((ip, port))
                    self._peers.append(peer)
                    
    async def add_peers_by_connections(self, peers: list[(asyncio.StreamReader, asyncio.StreamWriter)]):
        """Adds only the new peers to the list of peers"""
        async with self._peers_lock:
            for reader, writer in peers:
                peer = PeerConnection.from_connection(reader, writer, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                if (peer._host, peer._port) not in self._peers_info:
                    self._peers_info.append((peer._host, peer._port))
                    self._peers.append(peer)

    async def add_incoming_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, remote_peer_id: bytes) -> bool:
        peer = PeerConnection.from_connection(reader, writer, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
        await peer.accept_handshake(remote_peer_id)
        if not await peer.start_message_loop():
            await peer.close()
            return False
        if self._is_seeding:
            await peer.start_seeding()

        async with self._peers_lock:
            if (peer._host, peer._port) not in self._peers_info:
                self._peers_info.append((peer._host, peer._port))
                self._peers.append(peer)
        return True

    async def connect_to_peers(self):
        """Connects to all registered peers and starts periodic reconnection."""
        async with self._peers_lock:
            peers = list(self._peers)

        await asyncio.gather(*(self._connect_to_peer(peer) for peer in peers))

        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def get_peers(self) -> List[PeerConnection] | None:
        async with self._peers_lock:
            return list(self._peers)
        return None


    async def _connect_to_peer(self, peer: PeerConnection) -> bool:
        try:
            if not await peer.is_connected():
                if not await peer.connect():
                    print(f"Failed to connect to peer {peer._host}:{peer._port}")
                    return False

            if not await peer.is_message_loop_running():
                if not await peer.start_message_loop():
                    print(f"Failed to start message loop for peer {peer._host}:{peer._port}")
                    return False

            return True
        except Exception as e:
            print(f"Exception connecting to peer {peer._host}:{peer._port} - {e}")
            return False

    async def close_connections(self):
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
            
        async with self._peers_lock:
            for peer in self._peers:
                await peer.close()

    async def start_seeding(self):
        self._is_seeding = True
        async with self._peers_lock:
            for peer in self._peers:
                await peer.start_seeding()

    async def stop_seeding(self):
        self._is_seeding = False
        async with self._peers_lock:
            for peer in self._peers:
                await peer.stop_seeding()
