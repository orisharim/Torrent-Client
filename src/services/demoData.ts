// ─────────────────────────────────────────────────────────────────────────────
// REPLACE: demo fallback data.
// Used ONLY when the Tauri backend is unreachable (plain-browser dev) or a stub
// command returns empty results — see services/backend.ts withFallback().
// Safe to delete this whole file once the src-tauri commands return real data.
// ─────────────────────────────────────────────────────────────────────────────
import type {
  AddTorrentPayload,
  HomeStats,
  SearchResult,
  Torrent,
  TorrentDetail,
  TorrentPageStats,
} from "./types";

export const DEMO_TORRENTS: Torrent[] = [
  { id: 1, name: "Ubuntu 24.04.2 Desktop amd64.iso",        size: 5.8,  progress: 42,  speed: 3.2, status: "Downloading" },
  { id: 2, name: "Debian 13.1 netinst.iso",                 size: 0.7,  progress: 88,  speed: 1.4, status: "Downloading" },
  { id: 3, name: "Big Buck Bunny 4K (Open Movie)",          size: 12.4, progress: 100, speed: 0.8, status: "Seeding"     },
  { id: 4, name: "LibreOffice 25.2 Installer Pack",         size: 1.2,  progress: 15,  speed: 0,   status: "Paused"      },
  { id: 5, name: "Blender 4.5 LTS + Assets Bundle",         size: 3.6,  progress: 100, speed: 0,   status: "Completed"   },
  { id: 6, name: "Arch Linux 2026.06.01 dual.iso",          size: 1.1,  progress: 64,  speed: 2.1, status: "Downloading" },
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

const SEARCH_TEMPLATES: { suffix: string; size: number; seeds: number; peers: number; source: string }[] = [
  { suffix: "(2026) 1080p WEB-DL",        size: 4.2,  seeds: 1240, peers: 310, source: "OpenTracker" },
  { suffix: "Complete Season Pack",       size: 18.6, seeds: 860,  peers: 190, source: "TorrentHub"  },
  { suffix: "2160p 4K HDR",               size: 22.4, seeds: 410,  peers: 95,  source: "OpenTracker" },
  { suffix: "720p x265 HEVC",             size: 1.4,  seeds: 350,  peers: 120, source: "SeedBay"     },
  { suffix: "Official Release + Extras",  size: 7.8,  seeds: 150,  peers: 40,  source: "TorrentHub"  },
  { suffix: "Audiobook / EPUB Bundle",    size: 0.6,  seeds: 95,   peers: 22,  source: "SeedBay"     },
  { suffix: "REPACK Multi-Language",      size: 11.2, seeds: 28,   peers: 9,   source: "OpenTracker" },
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
});
