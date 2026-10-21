import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useTorrent } from "../hooks/useTorrent";
import type { TorrentStatus } from "../services/types";

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

type TorrentContextType = {
  torrents: Torrent[];
  loading: boolean;
  selected: Set<string>;
  setSelected: React.Dispatch<React.SetStateAction<Set<string>>>;
  toggleSelect: (id: string) => void;
  addTorrent: (torrentFilePath: string, downloadPath: string) => Promise<void>;
  pauseTorrent: (id: string) => void;
  resumeTorrent: (id: string) => void;
  pauseAll: () => void;
  pauseSelected: () => void;
  deleteTorrents: (ids: string[]) => void;
  updateTorrentStatus: (id: string, status: TorrentStatus) => void;
  setTorrentFlags: (id: string, isDownloading: boolean, isSeeding: boolean) => void;
  clearCompleted: () => void;
};

const TorrentContext = createContext<TorrentContextType>({
  torrents: [],
  loading: true,
  selected: new Set(),
  setSelected: () => {},
  toggleSelect: () => {},
  addTorrent: async () => {},
  pauseTorrent: () => {},
  resumeTorrent: () => {},
  pauseAll: () => {},
  pauseSelected: () => {},
  deleteTorrents: () => {},
  updateTorrentStatus: () => {},
  setTorrentFlags: () => {},
  clearCompleted: () => {},
});

export const useTorrents = () => useContext(TorrentContext);

const deriveStatus = (t: { is_downloading: boolean; is_seeding: boolean; downloaded_pieces: number; total_pieces: number }): TorrentStatus => {
  if (t.is_downloading) return "Downloading";
  if (t.is_seeding) return "Seeding";
  if (t.total_pieces > 0 && t.downloaded_pieces >= t.total_pieces) return "Completed";
  return "Paused";
};

const torrentName = (torrentFilePath: string) => {
  const base = torrentFilePath.split(/[\\/]/).pop() ?? torrentFilePath;
  return base.replace(/\.torrent$/i, "");
};

export const TorrentProvider = ({ children }: { children: React.ReactNode }) => {
  const {
    torrents: rawTorrents, loading,
    addTorrent: hookAddTorrent, pauseTorrent: hookPauseTorrent, resumeTorrent: hookResumeTorrent,
    deleteTorrent: hookDeleteTorrent, setStatus,
  } = useTorrent();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const torrents = useMemo<Torrent[]>(() => rawTorrents.map((t) => ({
    id: t.info_hash,
    name: torrentName(t.torrentFilePath),
    size: (t.total_size ?? 0) / 1024 ** 3,
    progress: t.total_pieces > 0 ? (t.downloaded_pieces / t.total_pieces) * 100 : 0,
    speed: Math.round(t.download_speed * 100) / 100,
    status: deriveStatus(t),
    isDownloading: t.is_downloading,
    isSeeding: t.is_seeding,
    peers: t.connected_peers,
  })), [rawTorrents]);

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }, []);

  const addTorrent = useCallback(async (torrentFilePath: string, downloadPath: string) => {
    await hookAddTorrent(torrentFilePath, downloadPath);
  }, [hookAddTorrent]);

  const findByInfoHash = useCallback(
    (id: string) => rawTorrents.find((t) => t.info_hash === id),
    [rawTorrents],
  );

  const pauseTorrent = useCallback((id: string) => {
    const raw = findByInfoHash(id);
    if (raw) hookPauseTorrent(id, raw.download_path);
  }, [findByInfoHash, hookPauseTorrent]);

  const resumeTorrent = useCallback((id: string) => {
    const raw = findByInfoHash(id);
    if (raw) hookResumeTorrent(id, raw.download_path);
  }, [findByInfoHash, hookResumeTorrent]);

  const pauseAll = useCallback(() => {
    rawTorrents.filter((t) => t.is_downloading).forEach((t) => hookPauseTorrent(t.info_hash, t.download_path));
  }, [rawTorrents, hookPauseTorrent]);

  const pauseSelected = useCallback(() => {
    rawTorrents
      .filter((t) => selected.has(t.info_hash) && t.is_downloading)
      .forEach((t) => hookPauseTorrent(t.info_hash, t.download_path));
  }, [rawTorrents, selected, hookPauseTorrent]);

  const deleteTorrents = useCallback((ids: string[]) => {
    ids.forEach((id) => {
      const raw = findByInfoHash(id);
      if (raw) hookDeleteTorrent(id, raw.download_path);
    });
    setSelected((prev) => { const next = new Set(prev); ids.forEach((id) => next.delete(id)); return next; });
  }, [findByInfoHash, hookDeleteTorrent]);

  const updateTorrentStatus = useCallback((id: string, status: TorrentStatus) => {
    if (status === "Downloading") resumeTorrent(id);
    else if (status === "Paused") pauseTorrent(id);
    else if (status === "Seeding") {
      const raw = findByInfoHash(id);
      if (raw) setStatus(id, raw.download_path, false, true);
    }
  }, [resumeTorrent, pauseTorrent, findByInfoHash, setStatus]);

  const setTorrentFlags = useCallback((id: string, isDownloading: boolean, isSeeding: boolean) => {
    const raw = findByInfoHash(id);
    if (raw) setStatus(id, raw.download_path, isDownloading, isSeeding);
  }, [findByInfoHash, setStatus]);

  const clearCompleted = useCallback(() => {
    rawTorrents
      .filter((t) => !t.is_downloading && !t.is_seeding && t.total_pieces > 0 && t.downloaded_pieces >= t.total_pieces)
      .forEach((t) => hookDeleteTorrent(t.info_hash, t.download_path));
  }, [rawTorrents, hookDeleteTorrent]);

  return (
    <TorrentContext.Provider
      value={{
        torrents, loading,
        selected, setSelected, toggleSelect,
        addTorrent, pauseTorrent, resumeTorrent, pauseAll, pauseSelected,
        deleteTorrents, updateTorrentStatus, setTorrentFlags, clearCompleted,
      }}
    >
      {children}
    </TorrentContext.Provider>
  );
};
