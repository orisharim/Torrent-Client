import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useTorrent } from "../hooks/useTorrent";
import type { TorrentStatus } from "../services/types";

export type Torrent = {
  id: string; // torrentFilePath
  name: string;
  size: number; // TODO: backend doesn't report a byte size yet — always 0 for now
  progress: number; // 0-100
  speed: number; // MB/s
  status: TorrentStatus;
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
    id: t.torrentFilePath,
    name: torrentName(t.torrentFilePath),
    size: 0,
    progress: t.total_pieces > 0 ? (t.downloaded_pieces / t.total_pieces) * 100 : 0,
    speed: t.download_speed,
    status: deriveStatus(t),
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

  const pauseTorrent = useCallback((id: string) => { hookPauseTorrent(id); }, [hookPauseTorrent]);
  const resumeTorrent = useCallback((id: string) => { hookResumeTorrent(id); }, [hookResumeTorrent]);

  const pauseAll = useCallback(() => {
    rawTorrents.filter((t) => t.is_downloading).forEach((t) => hookPauseTorrent(t.torrentFilePath));
  }, [rawTorrents, hookPauseTorrent]);

  const pauseSelected = useCallback(() => {
    rawTorrents
      .filter((t) => selected.has(t.torrentFilePath) && t.is_downloading)
      .forEach((t) => hookPauseTorrent(t.torrentFilePath));
  }, [rawTorrents, selected, hookPauseTorrent]);

  const deleteTorrents = useCallback((ids: string[]) => {
    ids.forEach((id) => hookDeleteTorrent(id));
    setSelected((prev) => { const next = new Set(prev); ids.forEach((id) => next.delete(id)); return next; });
  }, [hookDeleteTorrent]);

  const updateTorrentStatus = useCallback((id: string, status: TorrentStatus) => {
    if (status === "Downloading") hookResumeTorrent(id);
    else if (status === "Paused") hookPauseTorrent(id);
    else if (status === "Seeding") setStatus(id, false, true);
  }, [hookResumeTorrent, hookPauseTorrent, setStatus]);

  const clearCompleted = useCallback(() => {
    rawTorrents
      .filter((t) => !t.is_downloading && !t.is_seeding && t.total_pieces > 0 && t.downloaded_pieces >= t.total_pieces)
      .forEach((t) => hookDeleteTorrent(t.torrentFilePath));
  }, [rawTorrents, hookDeleteTorrent]);

  return (
    <TorrentContext.Provider
      value={{
        torrents, loading,
        selected, setSelected, toggleSelect,
        addTorrent, pauseTorrent, resumeTorrent, pauseAll, pauseSelected,
        deleteTorrents, updateTorrentStatus, clearCompleted,
      }}
    >
      {children}
    </TorrentContext.Provider>
  );
};
