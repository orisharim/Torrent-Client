import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as torrentService from "../services/torrentService";
import type { AddTorrentPayload, Torrent } from "../services/types";

// Re-export so existing imports from this file continue to work
export type { Torrent } from "../services/types";

type TorrentContextType = {
  torrents: Torrent[];
  setTorrents: React.Dispatch<React.SetStateAction<Torrent[]>>;
  loading: boolean;
  selected: Set<number>;
  setSelected: React.Dispatch<React.SetStateAction<Set<number>>>;
  toggleSelect: (id: number) => void;
  addTorrent: (payload: AddTorrentPayload) => Promise<Torrent>;
  pauseTorrent: (id: number) => void;
  resumeTorrent: (id: number) => void;
  pauseAll: () => void;
  pauseSelected: () => void;
  deleteTorrents: (ids: number[]) => void;
  updateTorrentStatus: (id: number, status: Torrent["status"]) => void;
  clearCompleted: () => void;
};

const TorrentContext = createContext<TorrentContextType>({
  torrents: [],
  setTorrents: () => {},
  loading: true,
  selected: new Set(),
  setSelected: () => {},
  toggleSelect: () => {},
  addTorrent: async () => ({ id: 0, name: "", size: 0, progress: 0, speed: 0, status: "Paused", health: "Good" }),
  pauseTorrent: () => {},
  resumeTorrent: () => {},
  pauseAll: () => {},
  pauseSelected: () => {},
  deleteTorrents: () => {},
  updateTorrentStatus: () => {},
  clearCompleted: () => {},
});

export const useTorrents = () => useContext(TorrentContext);

export const TorrentProvider = ({ children }: { children: React.ReactNode }) => {
  const [torrents, setTorrents] = useState<Torrent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  // Initial load from service — swap torrentService.getTorrents for real API call
  useEffect(() => {
    torrentService.getTorrents().then((list) => {
      setTorrents(list);
      setLoading(false);
    });
  }, []);

  // Demo simulation — remove this block when connecting real-time API/WebSocket
  useEffect(() => {
    const interval = setInterval(() => {
      setTorrents((prev) =>
        prev.map((torrent) => {
          if (torrent.status !== "Downloading") return torrent;
          const newProgress = Math.min(torrent.progress + Math.random() * 3, 100);
          return {
            ...torrent,
            progress: newProgress,
            speed: newProgress >= 100 ? 0 : Number((Math.random() * 5).toFixed(1)),
            status: newProgress >= 100 ? "Completed" : "Downloading",
          };
        })
      );
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleSelect = useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }, []);

  const addTorrent = useCallback(async (payload: AddTorrentPayload): Promise<Torrent> => {
    const result = await torrentService.addTorrent(payload);
    let added: Torrent = result;
    setTorrents((prev) => {
      // REPLACE: engine returns real unique ids — stub always returns id: 0
      const id = result.id === 0 || prev.some((t) => t.id === result.id) ? Date.now() : result.id;
      added = { ...result, id };
      return [...prev, added];
    });
    return added;
  }, []);

  const pauseTorrent = useCallback((id: number) => {
    torrentService.pauseTorrent(id); // REPLACE: optimistic update, rollback on error
    setTorrents((prev) => prev.map((torrent) => (torrent.id === id ? { ...torrent, status: "Paused", speed: 0 } : torrent)));
  }, []);

  const resumeTorrent = useCallback((id: number) => {
    torrentService.resumeTorrent(id); // REPLACE: optimistic update, rollback on error
    setTorrents((prev) =>
      prev.map((torrent) => (torrent.id === id && torrent.progress < 100 ? { ...torrent, status: "Downloading", speed: 1.5 } : torrent))
    );
  }, []);

  const pauseAll = useCallback(() => {
    torrents
      .filter((torrent) => torrent.status === "Downloading")
      .forEach((torrent) => torrentService.pauseTorrent(torrent.id)); // REPLACE: batch API call
    setTorrents((prev) =>
      prev.map((torrent) => (torrent.status === "Downloading" ? { ...torrent, status: "Paused", speed: 0 } : torrent))
    );
  }, [torrents]);

  const pauseSelected = useCallback(() => {
    torrents
      .filter((torrent) => selected.has(torrent.id) && torrent.status === "Downloading")
      .forEach((torrent) => torrentService.pauseTorrent(torrent.id)); // REPLACE: batch API call
    setTorrents((prev) =>
      prev.map((torrent) =>
        selected.has(torrent.id) && torrent.status === "Downloading" ? { ...torrent, status: "Paused", speed: 0 } : torrent
      )
    );
  }, [torrents, selected]);

  const deleteTorrents = useCallback((ids: number[]) => {
    torrentService.deleteTorrents(ids); // REPLACE: await + error handling
    setTorrents((prev) => prev.filter((torrent) => !ids.includes(torrent.id)));
    setSelected((prev) => { const next = new Set(prev); ids.forEach((id) => next.delete(id)); return next; });
  }, []);

  const updateTorrentStatus = useCallback((id: number, status: Torrent["status"]) => {
    torrentService.updateTorrentStatus(id, status); // REPLACE: await + error handling
    setTorrents((prev) => prev.map((torrent) => (torrent.id === id ? { ...torrent, status } : torrent)));
  }, []);

  const clearCompleted = useCallback(() => {
    torrentService.clearCompleted(); // REPLACE: API call
    setTorrents((prev) => prev.filter((t) => t.status !== "Completed"));
  }, []);

  return (
    <TorrentContext.Provider
      value={{
        torrents, setTorrents, loading,
        selected, setSelected, toggleSelect,
        addTorrent, pauseTorrent, resumeTorrent, pauseAll, pauseSelected,
        deleteTorrents, updateTorrentStatus, clearCompleted,
      }}
    >
      {children}
    </TorrentContext.Provider>
  );
};
