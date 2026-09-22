export type TorrentStatus = "Downloading" | "Paused" | "Completed" | "Seeding";

export type SearchResult = {
  id: number;
  name: string;
  size: number; // GB, same convention as Torrent.size
  seeds: number;
  peers: number;
  source: string;
  magnet: string;
};

// field names match the real backend contract (confirmed against src/hooks/useSettings.ts, not guessed)
export type AppSettings = {
  max_connection: number; // 0 means unlimited
  download_speed: number; // MB/s, 0 means no limit
  upload_speed_limit: number; // MB/s, 0 means no limit
  tracker_amount: number; // amount of trackers to contact at once, 0 means all
  enable_receiving: boolean;
  enable_dht: boolean;
  enable_port_downloading: boolean;
};
