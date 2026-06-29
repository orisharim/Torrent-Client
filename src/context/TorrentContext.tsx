import React, { createContext, useContext, useEffect, useState } from "react";
import * as torrentService from "../services/torrentService";
import type { Torrent } from "../services/types";

// Re-export so existing imports from this file continue to work
export type { Torrent } from "../services/types";

type TorrentContextType = {
  torrents: Torrent[];
  setTorrents: React.Dispatch<React.SetStateAction<Torrent[]>>;
  clearCompleted: () => void;
};

const TorrentContext = createContext<TorrentContextType>({
  torrents: [],
  setTorrents: () => {},
  clearCompleted: () => {},
});

export const useTorrents = () => useContext(TorrentContext);

export const TorrentProvider = ({ children }: { children: React.ReactNode }) => {
  const [torrents, setTorrents] = useState<Torrent[]>([]);

  // Initial load from service — swap torrentService.getTorrents for real API call
  useEffect(() => {
    torrentService.getTorrents().then(setTorrents);
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

  const clearCompleted = () => {
    torrentService.clearCompleted(); // REPLACE: API call
    setTorrents((prev) => prev.filter((t) => t.status !== "Completed"));
  };

  return (
    <TorrentContext.Provider value={{ torrents, setTorrents, clearCompleted }}>
      {children}
    </TorrentContext.Provider>
  );
};
