from typing_extensions import Optional
from torrent_storage import TorrentStorage
from peers.peer_connection import PeerConnection
from typing import List, Tuple
from torrent import Torrent
import asyncio

class PeersManager:
    
    LISTEN_PORT: int = 6881
    RECONNECT_INTERVAL: float = 15.0
    
    def __init__(self, peers_info: List[Tuple[str, int]], torrent_metadata: Torrent, peer_id: bytes, torrent_storage: TorrentStorage) -> None:
        self._peers: List[PeerConnection] = []
        self._peers_lock: asyncio.Lock = asyncio.Lock() 
        self._torrent_metadata = torrent_metadata
        self._peer_id = peer_id
        self._torrent_storage = torrent_storage
        
        for ip, port in peers_info:
            peer = PeerConnection.from_address(ip, port, torrent_metadata.info_hash, peer_id, torrent_storage)
            self._peers.append(peer)

        self._server: Optional[asyncio.Server] = None
        self._reconnect_task: Optional[asyncio.Task] = None


    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = PeerConnection.from_connection(reader, writer, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
        if await self._connect_to_peer(peer):
            async with self._peers_lock:
                self._peers.append(peer)
    
    async def start_listening(self) -> bool:
        try:
            self._server = await asyncio.start_server(self._handle_connection, "", PeersManager.LISTEN_PORT)
        except Exception:
            print(f"Failed to start listening on port {PeersManager.LISTEN_PORT}")
            return False
        print(f"Listening on port {PeersManager.LISTEN_PORT}")
        return True

    async def stop_listening(self) -> bool:
        self._server.close()
        try:
            await self._server.wait_closed()
        except asyncio.CancelledError:
            pass
    
    async def _reconnect(self):
        while True:
            await asyncio.sleep(self.RECONNECT_INTERVAL)
            try:
                await self._connect_to_unconnected_peers()
            except Exception:
                pass

    async def set_peers(self, peers_info: list[tuple[str, int]]):
        """Closes all peer connections and sets the list of peers"""
        await self.close_connections()
        async with self._peers_lock:
            self._peers = []
            for ip, port in peers_info:
                peer = PeerConnection.from_address(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def add_peers(self, new_peers_info: list[tuple[str, int]]):
        """Adds new peers to the list of peers"""
        async with self._peers_lock:
            for ip, port in new_peers_info:
                peer = PeerConnection.from_address(ip, port, self._torrent_metadata.info_hash, self._peer_id, self._torrent_storage)
                self._peers.append(peer)

    async def get_peers(self) -> List[PeerConnection] | None:
        async with self._peers_lock:
            return list(self._peers)
        return None

    async def connect_to_peers(self) -> None:
        """Connects to any peers that are not currently connected"""
        await self._connect_to_unconnected_peers()
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _connect_to_unconnected_peers(self) -> None:
        async with self._peers_lock:
            peers_snapshot = list(self._peers)
        
        for peer in peers_snapshot:
            if not await peer.is_connected():
                asyncio.create_task(self._connect_to_peer(peer))

    async def _connect_to_peer(self, peer: PeerConnection) -> bool:
        try:
            success = await peer.connect()
            if not success:
                print(f"Failed to connect to peer {peer._host}:{peer._port}")
                return False

            success_loop = await peer.start_message_loop()
            if not success_loop:
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

