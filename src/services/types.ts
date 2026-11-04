export type TorrentStatus = "Downloading" | "Paused" | "Completed" | "Seeding";


// golbal setting only (flask has 3 fields)
export type GlobalSettings = {
  enable_receiving : boolean;
  enable_dht : boolean;
  enable_port_downloading : boolean;
};

// raw torrent as tracked by useTorrent (backend fields + the remembered .torrent path)
export type BackendTorrent = {
  torrentFilePath: string;
  info_hash: string;
  download_path: string;
  timestamp: number;
  download_speed: number;
  downloaded_pieces: number;
  total_pieces: number;
  total_size: number;
  is_downloading: boolean;
  is_seeding: boolean;
  connected_peers: number;
};

// torrent as displayed in the UI
export type Torrent = {
  id: string; // info_hash
  name: string;
  size: number; // GB
  progress: number; // 0-100
  speed: number; // MB/s
  status: TorrentStatus;
  isDownloading: boolean;
  isSeeding: boolean;
  peers: number;
};
