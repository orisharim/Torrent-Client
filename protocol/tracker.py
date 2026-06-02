import requests
import struct
import socket
from protocol.bencode import decode

def build_tracker_url(torrent, peer_id: bytes, port: int = 6881,
                      uploaded=0, downloaded=0, left=None):

    base = torrent.announce.decode()

    params = {
        "info_hash": encode_bytes(torrent.info_hash),
        "peer_id": encode_bytes(peer_id),
        "port": port,
        "uploaded": uploaded,
        "downloaded": downloaded,
        "left": (left if left is not None else torrent.length),
        "compact": 1
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())

    return base + "?" + query

def encode_bytes(b: bytes) -> str:
    return ''.join(f'%{byte:02x}' for byte in b)

def contact_tracker(torrent, peer_id: bytes, port: int = 6881,
                      uploaded=0, downloaded=0, left=None):
    url = build_tracker_url(torrent, peer_id, port, uploaded, downloaded, left)

    print("Tracker URL:", url)

    response = requests.get(url, timeout=10)

    return response.content  # bencoded response

def parse_compact_peers(peer_bytes: bytes):
    peers = []

    for i in range(0, len(peer_bytes), 6):
        ip_bytes = peer_bytes[i:i+4]
        port_bytes = peer_bytes[i+4:i+6]

        ip = socket.inet_ntoa(ip_bytes)
        port = struct.unpack(">H", port_bytes)[0]

        peers.append((ip, port))

    return peers

def get_peers(torrent, peer_id: bytes, port: int = 6881, uploaded=0, downloaded=0, left=None):
    raw = contact_tracker(torrent, peer_id, port, uploaded, downloaded, left)

    data, _, _ = decode(raw)

    if b'peers' not in data:
        return []

    return parse_compact_peers(data[b'peers'])