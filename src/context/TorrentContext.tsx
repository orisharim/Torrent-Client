import React, { createContext, useContext, useEffect, useState } from "react";

export type Torrent = {
  id: number;
  name: string;
  size: number;
  progress: number;
  speed: number;
  status: "Downloading" | "Paused" | "Completed" | "Seeding";
  health: string;
};

const initialTorrents: Torrent[] = [
  { id: 0, name: "ubuntu.iso",           size: 2.5,  progress: 75,  speed: 1.8, status: "Downloading", health: "Good"      },
  { id: 1, name: "movie.mp4",            size: 1.2,  progress: 50,  speed: 0,   status: "Paused",       health: "Medium"    },
  { id: 2, name: "game.zip",             size: 15.8, progress: 100, speed: 0.3, status: "Seeding",      health: "Excellent" },
  { id: 3, name: "music_album.flac",     size: 0.9,  progress: 80,  speed: 2.4, status: "Downloading",  health: "Good"      },
  { id: 4, name: "course_materials.pdf", size: 0.3,  progress: 100, speed: 0,   status: "Completed",    health: "Perfect"   },
  { id: 5, name: "linux_tools.tar.gz",   size: 4.7,  progress: 60,  speed: 0,   status: "Paused",       health: "Low"       },
  { id: 6, name: "series_episode.mkv",   size: 2.1,  progress: 30,  speed: 3.1, status: "Downloading",  health: "Medium"    },
];

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
  const [torrents, setTorrents] = useState<Torrent[]>(initialTorrents);

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
    setTorrents((prev) => prev.filter((t) => t.status !== "Completed"));
  };

  return (
    <TorrentContext.Provider value={{ torrents, setTorrents, clearCompleted }}>
      {children}
    </TorrentContext.Provider>
  );
};
