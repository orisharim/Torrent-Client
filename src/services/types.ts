export type TorrentStatus = "Downloading" | "Paused" | "Completed" | "Seeding";
export type TorrentHealth = "Perfect" | "Excellent" | "Good" | "Medium" | "Low";
export type DeviceType = "Desktop" | "Phone" | "Tablet";
export type DeviceStatus = "Online" | "Offline";
export type ProxyType = "None" | "SOCKS5" | "HTTP";

export type Torrent = {
  id: number;
  name: string;
  size: number;
  progress: number;
  speed: number;
  status: TorrentStatus;
  health: TorrentHealth;
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
  health: TorrentHealth;
  magnet: string;
};

export type FeedItem = {
  id: number;
  source: string;
  name: string;
  size: string;
  date: string;
};

export type FeedStats = {
  newToday: number;
  downloadsReady: number;
};

export type Device = {
  id: number;
  name: string;
  type: DeviceType;
  status: DeviceStatus;
  lastSeen: string;
};

export type AppSettings = {
  startOnStartup: boolean;
  minimizeToTray: boolean;
  language: string;
  savePath: string;
  downloadLimit: number;
  uploadLimit: number;
  autoStart: boolean;
  notifyOnComplete: boolean;
  listeningPort: number;
  enableUPnP: boolean;
  enableDHT: boolean;
  proxy: ProxyType;
  enableEncryption: boolean;
  anonymousMode: boolean;
  maxConnections: number;
  maxPeersPerTorrent: number;
};

export type HomeStats = {
  downloadSpeed: string;
  uploadSpeed: string;
  activeTorrents: number;
  seedingTorrents: number;
};
