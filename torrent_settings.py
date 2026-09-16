from attr import dataclass

@dataclass
class TorrentSettings:
    max_connections: int = 50 # 0 means unlimited
    download_speed_limit: float = 0  # in megabytes per second, 0 means no limit
    upload_speed_limit: float = 0  # in megabytes per second, 0 means no limit
    tracker_amount: int = 4 # amount of trackers to contact at once, 0 means all
    enable_receiving_peers: bool = True
    enable_dht: bool = True
    enable_port_forwarding: bool = True
