import React, { useEffect, useState } from "react";
import { Pause, Play, Trash2 } from "lucide-react";

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

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [pendingDelete, setPendingDelete] = useState<number[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setTorrents((prev) =>
        prev.map((t) => {
          if (t.status !== "Downloading") return t;
          const newProgress = Math.min(t.progress + Math.random() * 3, 100);
          return {
            ...t,
            progress: newProgress,
            speed: newProgress >= 100 ? 0 : Number((Math.random() * 5).toFixed(1)),
            status: newProgress >= 100 ? "Completed" : "Downloading",
          };
        })
      );
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelected(selected.size === torrents.length ? new Set() : new Set(torrents.map((t) => t.id)));
  };

  const pauseTorrent = (id: number) => {
    setTorrents((prev) => prev.map((t) => (t.id === id ? { ...t, status: "Paused", speed: 0 } : t)));
  };

  const stopAllTorrents = () => {
    setTorrents((prev) => prev.map((t) => (t.status === "Downloading" ? { ...t, status: "Paused", speed: 0 } : t)));
  };

  const resumeTorrent = (id: number) => {
    setTorrents((prev) =>
      prev.map((t) => (t.id === id && t.progress < 100 ? { ...t, status: "Downloading", speed: 1.5 } : t))
    );
  };

  const deleteTorrents = (ids: number[]) => {
    setTorrents((prev) => prev.filter((t) => !ids.includes(t.id)));
    setSelected((prev) => { const next = new Set(prev); ids.forEach((id) => next.delete(id)); return next; });
  };

  const pauseSelected = () => {
    setTorrents((prev) =>
      prev.map((t) => (selected.has(t.id) && t.status === "Downloading" ? { ...t, status: "Paused", speed: 0 } : t))
    );
  };

  const allSelected = torrents.length > 0 && selected.size === torrents.length;
  const someSelected = selected.size > 0 && !allSelected;

  return (
    <div className="bg-white dark:bg-stone-800 border border-blue-100 dark:border-blue-900 rounded-2xl overflow-hidden shadow-sm">
      {selected.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 dark:bg-blue-950 border-b border-blue-100 dark:border-blue-900">
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">{selected.size} selected</span>
          <button
            onClick={pauseSelected}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40 hover:bg-amber-200 dark:hover:bg-amber-800/40 transition-colors"
          >
            <Pause size={12} />
            Pause
          </button>
          <button
            onClick={() => setPendingDelete([...selected])}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
          >
            <Trash2 size={12} />
            Delete
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-blue-400 dark:text-blue-500 hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      <div className="overflow-y-auto max-h-120">
        <table className="w-full text-sm">
          <TableHead
            allSelected={allSelected}
            someSelected={someSelected}
            onToggleAll={toggleSelectAll}
            stopAllTorrents={stopAllTorrents}
          />
          <tbody>
            {torrents.map((torrent, index) => (
              <TableRow
                key={torrent.id}
                index={index}
                torrent={torrent}
                selected={selected.has(torrent.id)}
                onToggleSelect={toggleSelect}
                onPause={pauseTorrent}
                onResume={resumeTorrent}
                onAskDelete={(id) => setPendingDelete([id])}
              />
            ))}
          </tbody>
        </table>
      </div>

      {pendingDelete.length > 0 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-stone-800 rounded-2xl shadow-2xl w-80 p-6">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">
              Delete {pendingDelete.length > 1 ? `${pendingDelete.length} torrents` : "Torrent"}?
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPendingDelete([])}
                className="px-4 py-2 rounded-full text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/40 hover:bg-blue-100 dark:hover:bg-blue-800/60 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { deleteTorrents(pendingDelete); setPendingDelete([]); }}
                className="px-4 py-2 rounded-full text-sm font-medium text-white bg-red-500 hover:bg-red-600 transition-colors"
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

type TableHeadProps = {
  allSelected: boolean;
  someSelected: boolean;
  onToggleAll: () => void;
  stopAllTorrents: () => void;
};

const TableHead = ({ allSelected, someSelected, onToggleAll, stopAllTorrents }: TableHeadProps) => (
  <thead>
    <tr className="bg-blue-50 dark:bg-blue-950/60 text-xs font-semibold text-blue-500 dark:text-blue-400 uppercase tracking-wide border-b border-blue-100 dark:border-blue-900">
      <th className="px-4 py-3 w-8">
        <input
          type="checkbox"
          checked={allSelected}
          ref={(el) => { if (el) el.indeterminate = someSelected; }}
          onChange={onToggleAll}
          className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      </th>
      <th className="text-left px-4 py-3">Name</th>
      <th className="text-left px-4 py-3">Size</th>
      <th className="text-left px-4 py-3 w-48">Progress</th>
      <th className="text-left px-4 py-3">Speed</th>
      <th className="text-left px-4 py-3">Status</th>
      <th className="text-left px-4 py-3">Health</th>
      <th className="text-left px-4 py-3">Actions</th>
      <th className="px-4 py-3">
        <button
          onClick={stopAllTorrents}
          className="flex items-center gap-1.5 rounded-full bg-red-50 dark:bg-red-900/30 px-3 py-1.5 text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
        >
          <Pause size={12} />
          Stop All
        </button>
      </th>
    </tr>
  </thead>
);

const statusStyles: Record<string, string> = {
  Downloading: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Paused:      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  Completed:   "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  Seeding:     "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
};

const healthStyles: Record<string, string> = {
  Perfect:   "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  Excellent: "bg-green-100 text-green-600 dark:bg-green-900/40 dark:text-green-300",
  Good:      "bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-300",
  Medium:    "bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-300",
  Low:       "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400",
};

type TableRowProps = {
  index: number;
  torrent: Torrent;
  selected: boolean;
  onToggleSelect: (id: number) => void;
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onAskDelete: (id: number) => void;
};

const TableRow = ({ index, torrent, selected, onToggleSelect, onPause, onResume, onAskDelete }: TableRowProps) => (
  <tr className={`text-sm border-b border-blue-50 dark:border-blue-900/50 last:border-0 transition-colors hover:bg-blue-50/50 dark:hover:bg-blue-900/20 ${selected ? "bg-blue-50 dark:bg-blue-900/30" : index % 2 ? "bg-blue-50/30 dark:bg-blue-950/20" : "bg-white dark:bg-stone-800"}`}>
    <td className="px-4 py-3">
      <input
        type="checkbox"
        checked={selected}
        onChange={() => onToggleSelect(torrent.id)}
        className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
      />
    </td>

    <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-100">{torrent.name}</td>
    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{torrent.size} GB</td>

    <td className="px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-blue-100 dark:bg-blue-900/40 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-500 h-full rounded-full transition-all duration-500"
            style={{ width: `${torrent.progress}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">{Math.round(torrent.progress)}%</span>
      </div>
    </td>

    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
      {torrent.speed > 0 ? `${torrent.speed} MB/s` : "—"}
    </td>

    <td className="px-4 py-3">
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[torrent.status]}`}>
        {torrent.status}
      </span>
    </td>

    <td className="px-4 py-3">
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${healthStyles[torrent.health] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"}`}>
        {torrent.health}
      </span>
    </td>

    <td className="px-4 py-3">
      <div className="flex items-center gap-1">
        {(torrent.status === "Downloading" || torrent.status === "Seeding") && (
          <button
            onClick={() => onPause(torrent.id)}
            title="Pause"
            className="p-1.5 rounded-full text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors"
          >
            <Pause size={15} />
          </button>
        )}
        {torrent.status === "Paused" && (
          <button
            onClick={() => onResume(torrent.id)}
            title="Resume"
            className="p-1.5 rounded-full text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
          >
            <Play size={15} />
          </button>
        )}
        <button
          onClick={() => onAskDelete(torrent.id)}
          title="Delete"
          className="p-1.5 rounded-full text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </td>
    <td />
  </tr>
);
