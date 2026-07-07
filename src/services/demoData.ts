// ─────────────────────────────────────────────────────────────────────────────
// REPLACE: demo fallback data.
// Used ONLY when the Tauri backend is unreachable (plain-browser dev) or a stub
// command returns empty results — see services/backend.ts withFallback().
// Safe to delete this whole file once the src-tauri commands return real data.
// ─────────────────────────────────────────────────────────────────────────────
import type {
  AddTorrentPayload,
  Device,
  FeedItem,
  FeedStats,
  HomeStats,
  SearchResult,
  Torrent,
  TorrentDetail,
  TorrentHealth,
  TorrentPageStats,
} from "./types";

export const DEMO_TORRENTS: Torrent[] = [
  { id: 1, name: "Ubuntu 24.04.2 Desktop amd64.iso",        size: 5.8,  progress: 42,  speed: 3.2, status: "Downloading", health: "Perfect"   },
  { id: 2, name: "Debian 13.1 netinst.iso",                 size: 0.7,  progress: 88,  speed: 1.4, status: "Downloading", health: "Excellent" },
  { id: 3, name: "Big Buck Bunny 4K (Open Movie)",          size: 12.4, progress: 100, speed: 0.8, status: "Seeding",     health: "Good"      },
  { id: 4, name: "LibreOffice 25.2 Installer Pack",         size: 1.2,  progress: 15,  speed: 0,   status: "Paused",      health: "Medium"    },
  { id: 5, name: "Blender 4.5 LTS + Assets Bundle",         size: 3.6,  progress: 100, speed: 0,   status: "Completed",   health: "Excellent" },
  { id: 6, name: "Arch Linux 2026.06.01 dual.iso",          size: 1.1,  progress: 64,  speed: 2.1, status: "Downloading", health: "Low"       },
];

export const DEMO_TORRENT_DETAILS: TorrentDetail[] = DEMO_TORRENTS.map((torrent) => ({
  id: torrent.id,
  files: `${1 + (torrent.id % 4)} files`,
  info: torrent.name,
  peers: `${8 + torrent.id * 7} peers`,
  trackers: `${2 + (torrent.id % 3)} trackers`,
  speed: torrent.speed > 0 ? `${torrent.speed} MB/s` : "—",
}));

export const DEMO_TORRENT_PAGE_STATS: TorrentPageStats = {
  totalPeers: 143,
  currentSpeed: "6.7 MB/s",
};

export const DEMO_HOME_STATS: HomeStats = {
  downloadSpeed: "6.7 MB/s",
  uploadSpeed: "1.2 MB/s",
  activeTorrents: 3,
  seedingTorrents: 1,
};

export const DEMO_FEEDS: FeedItem[] = [
  { id: 1, source: "distrowatch.com", name: "Fedora 42 Workstation released",       size: "2.1 GB", date: "Today"     },
  { id: 2, source: "blender.org",     name: "Blender Open Movie: Charge (4K)",      size: "9.8 GB", date: "Today"     },
  { id: 3, source: "archive.org",     name: "Public Domain Film Pack — June",       size: "4.3 GB", date: "Yesterday" },
  { id: 4, source: "distrowatch.com", name: "Linux Mint 22.2 Cinnamon",             size: "2.9 GB", date: "2 days ago" },
];

export const DEMO_FEED_STATS: FeedStats = {
  newToday: 2,
  downloadsReady: 4,
};

export const DEMO_DEVICES: Device[] = [
  { id: 1, name: "Desktop-Main",   type: "Desktop", status: "Online",  lastSeen: "Now"         },
  { id: 2, name: "Dan's Phone",    type: "Phone",   status: "Online",  lastSeen: "5 min ago"   },
  { id: 3, name: "Living-Room-TV", type: "Tablet",  status: "Offline", lastSeen: "Yesterday"   },
];

const SEARCH_TEMPLATES: { suffix: string; size: number; seeds: number; peers: number; source: string; health: TorrentHealth }[] = [
  { suffix: "(2026) 1080p WEB-DL",        size: 4.2,  seeds: 1240, peers: 310, source: "OpenTracker",  health: "Perfect"   },
  { suffix: "Complete Season Pack",       size: 18.6, seeds: 860,  peers: 190, source: "TorrentHub",   health: "Excellent" },
  { suffix: "2160p 4K HDR",               size: 22.4, seeds: 410,  peers: 95,  source: "OpenTracker",  health: "Good"      },
  { suffix: "720p x265 HEVC",             size: 1.4,  seeds: 350,  peers: 120, source: "SeedBay",      health: "Good"      },
  { suffix: "Official Release + Extras",  size: 7.8,  seeds: 150,  peers: 40,  source: "TorrentHub",   health: "Medium"    },
  { suffix: "Audiobook / EPUB Bundle",    size: 0.6,  seeds: 95,   peers: 22,  source: "SeedBay",      health: "Medium"    },
  { suffix: "REPACK Multi-Language",      size: 11.2, seeds: 28,   peers: 9,   source: "OpenTracker",  health: "Low"       },
];

export const demoSearchResults = (query: string): SearchResult[] =>
  SEARCH_TEMPLATES.map((template, index) => {
    const name = `${query} ${template.suffix}`;
    return {
      id: index + 1,
      name,
      size: template.size,
      seeds: template.seeds,
      peers: template.peers,
      source: template.source,
      health: template.health,
      magnet: `magnet:?xt=urn:btih:${(index + 1).toString(16).padStart(40, "0")}&dn=${encodeURIComponent(name)}`,
    };
  });

const nameFromMagnet = (uri: string): string => {
  const match = /[?&]dn=([^&]+)/.exec(uri);
  return match ? decodeURIComponent(match[1].replace(/\+/g, " ")) : "New Torrent";
};

export const demoAddedTorrent = (payload: AddTorrentPayload): Torrent => ({
  id: Date.now(),
  name: payload.type === "magnet" ? nameFromMagnet(payload.uri) : payload.fileName.replace(/\.torrent$/i, ""),
  size: Number((0.5 + Math.random() * 9).toFixed(1)),
  progress: 0,
  speed: 1.5,
  status: "Downloading",
  health: "Good",
});
