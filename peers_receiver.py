
import asyncio
import TorrentSession.peers.peer_protocol_encoder as protocol_encoder
from TorrentSession.peers.peers import Peers

LISTENING_PORT = 6881
server: asyncio.Server | None = None
_peers_by_info_hash: dict[bytes, Peers] = {}
_registry_lock = asyncio.Lock()
 

async def register_peers(info_hash: bytes, peers: Peers) -> None:
    async with _registry_lock:
        _peers_by_info_hash[info_hash] = peers


async def unregister_peers(info_hash: bytes, peers: Peers) -> None:
    async with _registry_lock:
        if _peers_by_info_hash.get(info_hash) is peers:
            del _peers_by_info_hash[info_hash]


async def start_listening(listening_port: int = LISTENING_PORT) -> bool:
    global server
    if server is not None:
        return True
    try:
        server = await asyncio.start_server(
            handle_peer_connection, "", listening_port
        )
    except OSError as exc:
        print(f"Failed to start incoming peer listener on port {listening_port}: {exc}")
        return False
    print(f"Listening for incoming peers on port {listening_port}")
    return True


async def stop_listening() -> None:
    global server
    if server is None:
        return
    active_server = server
    server = None
    active_server.close()
    await active_server.wait_closed()

async def handle_peer_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        handshake = await reader.readexactly(68)
        info_hash, remote_peer_id = protocol_encoder.unpack_handshake(handshake)
        async with _registry_lock:
            peers = _peers_by_info_hash.get(info_hash)
        if peers is None:
            raise ValueError("unknown torrent info-hash")

        writer.write(protocol_encoder.pack_handshake(info_hash, peers._peer_id))
        await writer.drain()
        if not await peers.add_incoming_connection(reader, writer, remote_peer_id):
            raise ConnectionError("failed to start incoming peer")
    except (asyncio.IncompleteReadError, ConnectionError, OSError, ValueError) as exc:
        print(f"Rejected incoming peer connection: {exc}")
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
    