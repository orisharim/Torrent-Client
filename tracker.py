import socket
import struct
import random
import urllib.parse
import urllib.request
import asyncio
from typing import List, Tuple, Dict, Any, Optional
from torrent_file import TorrentFile
from bencode import decode_bencode

CONTACT_TIMEOUT = 10

# events: (str is for the http and the num is for the udp)
KEEP_ALIVE = ("", 0)
COMPLETED = ("completed", 1)
STARTED = ("started", 2)
STOPPED = ("stopped", 3)

def _parse_compact_peers(peer_bytes: bytes) -> List[Tuple[str, int]]:
    #Parse IPv4 compact peer binary data (6 bytes per peer)
    peers = []
    for i in range(0, len(peer_bytes), 6):
        if i + 6 > len(peer_bytes):
            break
        ip_bytes = peer_bytes[i:i+4]
        port_bytes = peer_bytes[i+4:i+6]
        ip = socket.inet_ntoa(ip_bytes)
        port = struct.unpack(">H", port_bytes)[0]
        peers.append((ip, port))
    return peers


def _parse_compact_peers6(peer_bytes: bytes) -> List[Tuple[str, int]]:
    #Parse IPv6 compact peer binary data (18 bytes per peer)
    peers = []
    for i in range(0, len(peer_bytes), 18):
        if i + 18 > len(peer_bytes):
            break
        ip_bytes = peer_bytes[i:i+16]
        port_bytes = peer_bytes[i+16:i+18]
        ip = socket.inet_ntop(socket.AF_INET6, ip_bytes)
        port = struct.unpack(">H", port_bytes)[0]
        peers.append((ip, port))
    return peers


def _extract_interval(tracker_res: dict) -> Optional[int]:
    #Extract interval integer from HTTP or UDP tracker response dictionary
    if not tracker_res or not isinstance(tracker_res, dict):
        return None
    interval = tracker_res.get(b'interval') or tracker_res.get('interval')
    return int(interval) if interval is not None else None


def _extract_peers_from_dict(tracker_res: dict) -> List[Tuple[str, int]]:
    #Extract list of (ip, port) tuples from HTTP/UDP tracker response dictionary
    if not tracker_res or not isinstance(tracker_res, dict):
        return []

    peers = []

    # Handle 'peers' key (dict list or compact bytes)
    peers_data = tracker_res.get(b'peers') or tracker_res.get('peers')
    if isinstance(peers_data, list):
        for p in peers_data:
            if isinstance(p, dict):
                ip = p.get(b'ip') or p.get('ip')
                port = p.get(b'port') or p.get('port')
                if ip and port:
                    ip_str = ip.decode('utf-8', errors='ignore') if isinstance(ip, bytes) else str(ip)
                    peers.append((ip_str, int(port)))
    elif isinstance(peers_data, bytes):
        peers.extend(_parse_compact_peers(peers_data))

    # Handle 'peers6' key (IPv6 compact bytes)
    peers6_data = tracker_res.get(b'peers6') or tracker_res.get('peers6')
    if isinstance(peers6_data, bytes):
        peers.extend(_parse_compact_peers6(peers6_data))

    return peers


def _parse_tracker_response(tracker_res: dict) -> Tuple[Optional[int], List[Tuple[str, int]]]:
    
    if not tracker_res or not isinstance(tracker_res, dict):
        return None, []

    interval = _extract_interval(tracker_res)
    peers = _extract_peers_from_dict(tracker_res)
    return interval, peers


async def get_peers(
    torrent_file: TorrentFile,
    peer_id: bytes,
    listening_port: int = 6881,
    event: Tuple[str, int] = KEEP_ALIVE,
    downloaded: int = 0,
    uploaded: int = 0,
    left: int = None
) -> Tuple[Optional[int], List[Tuple[str, int]]]:
    #contacts trackers and returns a tuple of (interval of when to contact next, list_of_peers)
    res = await contact_tracker(
        torrent_file=torrent_file,
        peer_id=peer_id,
        listening_port=listening_port,
        event=event,
        downloaded=downloaded,
        uploaded=uploaded,
        left=left
    )
    if res:
        return _parse_tracker_response(res)
    return None, []


async def contact_tracker(
    torrent_file: TorrentFile,
    peer_id: bytes,
    listening_port: int,
    event: Tuple[str, int] = KEEP_ALIVE,
    downloaded: int = 0,
    uploaded: int = 0,
    left: int = None
) -> Optional[Dict[str, Any]]:

    event_str = event[0] if event else ""
    event_num = event[1] if event else 0
    if left is None:
        left = torrent_file.length

    for tracker_url in torrent_file.trackers:
        print(f"Contacting tracker: {tracker_url}")
        try:
            res = None

            if tracker_url.startswith("udp"):
                res = await asyncio.to_thread(
                    _contact_udp_tracker,
                    tracker_url,
                    torrent_file.info_hash,
                    peer_id,
                    listening_port,
                    left,
                    downloaded,
                    uploaded,
                    event_num
                )
            elif tracker_url.startswith("http"):
                res = await asyncio.to_thread(
                    _contact_http_tracker,
                    tracker_url,
                    torrent_file.info_hash,
                    peer_id,
                    listening_port,
                    left,
                    downloaded,
                    uploaded,
                    event_str
                )

            if res is not None:
                return res

        except Exception as e:
            print(f"Failed to contact {tracker_url}: {e}")
            continue

    print("Failed to connect to any tracker")
    return None


def _contact_http_tracker(
    tracker_url: str,
    info_hash: bytes,
    peer_id: bytes,
    listening_port: int,
    left: int,
    downloaded: int = 0,
    uploaded: int = 0,
    event: str = ""
) -> Dict[bytes, Any]:
    params = {
        "info_hash": urllib.parse.quote_from_bytes(info_hash),
        "peer_id": urllib.parse.quote_from_bytes(peer_id),
        "port": str(listening_port),
        "uploaded": str(uploaded),
        "downloaded": str(downloaded),
        "left": str(left),
        "compact": "1",
    }

    if event:
        params["event"] = event

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{tracker_url}?{query_string}"

    req = urllib.request.Request(full_url, headers={"User-Agent": "MyTorrentClient/1.0"})
    with urllib.request.urlopen(req, timeout=CONTACT_TIMEOUT) as response:
        raw_data = response.read()
        data, _, _ = decode_bencode(raw_data)
        return data


def _contact_udp_tracker(
    tracker_url: str,
    info_hash: bytes,
    peer_id: bytes,
    listening_port: int,
    left: int,
    downloaded: int = 0,
    uploaded: int = 0,
    event: int = 0
) -> Dict[str, Any]:

    parsed_url = urllib.parse.urlparse(tracker_url)

    #connect request (BEP 0015)
    protocol_id = 0x41727101980
    action_connect = 0
    transaction_id = random.randint(0, 0xFFFFFFFF)
    packet = struct.pack(">QII", protocol_id, action_connect, transaction_id)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(CONTACT_TIMEOUT)
    try:
        sock.sendto(packet, (parsed_url.hostname, parsed_url.port or 80))
        data, _ = sock.recvfrom(2048)

        if len(data) < 16:
            raise ValueError("Invalid connect response size")

        rec_action, rec_trans_id, connection_id = struct.unpack(">IIQ", data[:16])

        if rec_action != 0 or rec_trans_id != transaction_id:
            raise ValueError("Transaction ID mismatch or bad connect action")

        # announce request
        action_announce = 1
        transaction_id = random.randint(0, 0xFFFFFFFF)
        key = random.randint(0, 0xFFFFFFFF)
        num_want = -1

        announce_packet = struct.pack(
            ">QII20s20sQQQIIIiH",
            connection_id,
            action_announce,
            transaction_id,
            info_hash,
            peer_id,
            downloaded,
            left,
            uploaded,
            event,
            0,  #ip address 0 is the default and lets the os decide
            key,
            num_want,
            listening_port
        )
        sock.sendto(announce_packet, (parsed_url.hostname, parsed_url.port or 80))

        # announce response
        announce_res, _ = sock.recvfrom(2048)
        if len(announce_res) < 20:
            raise ValueError("Invalid announce response size")

        res_action, res_trans_id, interval, leechers, seeders = struct.unpack(
            ">IIIII", announce_res[:20]
        )

        if res_action == 3:  # Tracker error action
            error_msg = announce_res[8:].decode('utf-8', errors='ignore')
            raise ValueError(f"Tracker error: {error_msg}")

        if res_action != 1 or res_trans_id != transaction_id:
            raise ValueError("Transaction ID mismatch or bad announce action")

        peer_bytes = announce_res[20:]

        return {
            "interval": interval,
            "leechers": leechers,
            "seeders": seeders,
            "peers": peer_bytes
        }
    finally:
        sock.close()
