import React, { useEffect, useState } from "react";
import { MoreVertical, Pause, Play, Trash2 } from "lucide-react";

type Torrent = {
  id: number;
  name: string;
  size: number;
  progress: number;
  speed: number;
  status: "Downloading" | "Paused" | "Completed" | "Seeding";
  health: string;
};

export const TorrentTable = () => {
  const [torrents, setTorrents] = useState<Torrent[]>([
    { id: 0, name: "ubuntu.iso", size: 2.5, progress: 75, speed: 1.8, status: "Downloading", health: "Good" },
    { id: 1, name: "movie.mp4", size: 1.2, progress: 50, speed: 0, status: "Paused", health: "Medium" },
    { id: 2, name: "game.zip", size: 15.8, progress: 100, speed: 0.3, status: "Seeding", health: "Excellent" },
    { id: 3, name: "music_album.flac", size: 0.9, progress: 80, speed: 2.4, status: "Downloading", health: "Good" },
    { id: 4, name: "course_materials.pdf", size: 0.3, progress: 100, speed: 0, status: "Completed", health: "Perfect" },
    { id: 5, name: "linux_tools.tar.gz", size: 4.7, progress: 60, speed: 0, status: "Paused", health: "Low" },
    { id: 6, name: "series_episode.mkv", size: 2.1, progress: 30, speed: 3.1, status: "Downloading", health: "Medium" },
  ]);

  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setTorrents((prev) =>
        prev.map((torrent) => {
          if (torrent.status !== "Downloading") return torrent;

          const newProgress = Math.min(
            torrent.progress + Math.random() * 3,
            100
          );

          return {
            ...torrent,
            progress: newProgress,
            speed:
              newProgress >= 100
                ? 0
                : Number((Math.random() * 5).toFixed(1)),
            status: newProgress >= 100 ? "Completed" : "Downloading",
          };
        })
      );
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const pauseTorrent = (id: number) => {
    setTorrents((prev) =>
      prev.map((torrent) =>
        torrent.id === id
          ? { ...torrent, status: "Paused", speed: 0 }
          : torrent
      )
    );
  };

  const resumeTorrent = (id: number) => {
    setTorrents((prev) =>
      prev.map((torrent) =>
        torrent.id === id && torrent.progress < 100
          ? { ...torrent, status: "Downloading", speed: 1.5 }
          : torrent
      )
    );
  };

  const deleteTorrent = (id: number) => {
    setTorrents((prev) => prev.filter((torrent) => torrent.id !== id));
  };

  return (
    <div className="p-4 w-full">
      <table className="w-full bg-stone-50 rounded-md">
        <TableHead />

        <tbody>
          {torrents.map((torrent, index) => (
            <TableRow
              key={torrent.id}
              index={index}
              torrent={torrent}
              onPause={pauseTorrent}
              onResume={resumeTorrent}
              onAskDelete={setDeleteId}
            />
          ))}
        </tbody>
      </table>

      {deleteId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[9999]">
          <div className="bg-white p-6 rounded shadow-lg w-80">
            <h2 className="text-lg font-semibold mb-3">Delete Torrent?</h2>

            <p className="text-sm mb-6">
              Are you sure you want to delete this torrent?
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteId(null)}
                className="px-3 py-1 rounded bg-stone-300 hover:bg-stone-400"
              >
                Cancel
              </button>

              <button
                onClick={() => {
                  deleteTorrent(deleteId);
                  setDeleteId(null);
                }}
                className="px-3 py-1 rounded bg-red-600 text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const TableHead = () => {
  return (
    <thead>
      <tr className="text-sm border-b border-stone-300">
        <th className="text-start p-1.5">Name</th>
        <th className="text-start p-1.5">Size</th>
        <th className="text-start p-1.5">Progress</th>
        <th className="text-start p-1.5">Speed</th>
        <th className="text-start p-1.5">Status</th>
        <th className="text-start p-1.5">Health</th>
        <th className="text-start p-1.5">Actions</th>
      </tr>
    </thead>
  );
};

type TableRowProps = {
  index: number;
  torrent: Torrent;
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onAskDelete: (id: number) => void;
};

const TableRow = ({
  index,
  torrent,
  onPause,
  onResume,
  onAskDelete,
}: TableRowProps) => {
  const [open, setOpen] = useState(false);

  return (
    <tr className={`text-sm ${index % 2 ? "bg-stone-300" : ""}`}>
      <td className="p-1.5">{torrent.name}</td>
      <td className="p-1.5">{torrent.size}GB</td>

      <td className="p-1.5">
        <div className="w-full bg-stone-200 rounded-full h-5 overflow-hidden">
          <div
            className="bg-stone-500 h-full rounded-full text-center text-xs leading-5 transition-all duration-500"
            style={{ width: `${torrent.progress}%` }}
          >
            {Math.round(torrent.progress)}%
          </div>
        </div>
      </td>

      <td className="p-1.5">
        {torrent.speed > 0 ? `${torrent.speed} MB/s` : "0 MB/s"}
      </td>

      <td className="p-1.5">{torrent.status}</td>
      <td className="p-1.5">{torrent.health}</td>

      <td className="p-1.5 relative">
        <button
          onClick={() => setOpen(!open)}
          className="p-1 rounded hover:bg-stone-400"
          title="Actions"
        >
          <MoreVertical size={18} />
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-36 bg-white border border-stone-300 rounded shadow-md z-50">
            {(torrent.status === "Downloading" ||
              torrent.status === "Seeding") && (
              <button
                onClick={() => {
                  onPause(torrent.id);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-stone-200"
              >
                <Pause size={16} />
                Pause
              </button>
            )}

            {torrent.status === "Paused" && (
              <button
                onClick={() => {
                  onResume(torrent.id);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-stone-200"
              >
                <Play size={16} />
                Resume
              </button>
            )}

            <button
              onClick={() => {
                onAskDelete(torrent.id);
                setOpen(false);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-left text-red-600 hover:bg-red-100"
            >
              <Trash2 size={16} />
              Delete
            </button>
          </div>
        )}
      </td>
    </tr>
  );
};