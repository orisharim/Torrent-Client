export type TorrentStatus = "Downloading" | "Paused" | "Completed" | "Seeding";

export type Torrent = {
  id: number;
  name: string;
  size: number;
  progress: number;
  speed: number;
  status: TorrentStatus;
};

export type TorrentDetail = {
  id: number;
  files: string;
  info: string;
  peers: string;
  trackers: string;
  speed: string;
};

export type TorrentPageStats = {
  totalPeers: number;
  currentSpeed: string;
};

export type AddTorrentPayload =
  | { type: "magnet"; uri: string }
  | { type: "file"; fileName: string };

export type SearchResult = {
  id: number;
  name: string;
  size: number; // GB, same convention as Torrent.size
  seeds: number;
  peers: number;
  source: string;
  magnet: string;
};

export type AppSettings = {
  maxConnections: number; // 0 means unlimited
  downloadSpeedLimit: number; // MB/s, 0 means no limit
  uploadSpeedLimit: number; // MB/s, 0 means no limit
  trackerAmount: number; // amount of trackers to contact at once, 0 means all
  enableReceivingPeers: boolean;
  enableDht: boolean;
  enablePortForwarding: boolean;
};

export type HomeStats = {
  downloadSpeed: string;
  uploadSpeed: string;
  activeTorrents: number;
  seedingTorrents: number;
};
