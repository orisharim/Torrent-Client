import { useMemo, useState } from "react";
import { Pause, Play, Trash2 } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";
import { useTorrents, type Torrent } from "../../context/TorrentContext";

const editableStatuses = ["Downloading", "Paused", "Seeding"] as const;
const statusPriority: Record<Torrent["status"], number> = {
  Downloading: 0,
  Seeding: 1,
  Paused: 2,
  Completed: 3,
};

const formatEstimatedTime = (torrent: Torrent) => {
  if (torrent.status !== "Downloading" || torrent.speed <= 0 || torrent.progress >= 100) {
    return "—";
  }

  const remainingGb = torrent.size * (1 - torrent.progress / 100);
  const remainingMb = remainingGb * 1024;
  const seconds = Math.max(0, Math.round(remainingMb / torrent.speed));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
};

export const TorrentTable = () => {
  const { t } = useLanguage();
  const { torrents, setTorrents } = useTorrents();

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [pendingDelete, setPendingDelete] = useState<number[]>([]);

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelected(selected.size === torrents.length ? new Set() : new Set(torrents.map((torrent) => torrent.id)));
  };

  const pauseTorrent = (id: number) => {
    setTorrents((prev) => prev.map((torrent) => (torrent.id === id ? { ...torrent, status: "Paused", speed: 0 } : torrent)));
  };

  const stopAllTorrents = () => {
    setTorrents((prev) => prev.map((torrent) => (torrent.status === "Downloading" ? { ...torrent, status: "Paused", speed: 0 } : torrent)));
  };

  const resumeTorrent = (id: number) => {
    setTorrents((prev) =>
      prev.map((torrent) => (torrent.id === id && torrent.progress < 100 ? { ...torrent, status: "Downloading", speed: 1.5 } : torrent))
    );
  };

  const deleteTorrents = (ids: number[]) => {
    setTorrents((prev) => prev.filter((torrent) => !ids.includes(torrent.id)));
    setSelected((prev) => { const next = new Set(prev); ids.forEach((id) => next.delete(id)); return next; });
  };

  const updateTorrentStatus = (id: number, status: Torrent["status"]) => {
    setTorrents((prev) => prev.map((torrent) => (torrent.id === id ? { ...torrent, status } : torrent)));
  };

  const pauseSelected = () => {
    setTorrents((prev) =>
      prev.map((torrent) => (selected.has(torrent.id) && torrent.status === "Downloading" ? { ...torrent, status: "Paused", speed: 0 } : torrent))
    );
  };

  const sortedTorrents = useMemo(
    () => [...torrents].sort((a, b) => statusPriority[a.status] - statusPriority[b.status]),
    [torrents]
  );

  const allSelected = torrents.length > 0 && selected.size === torrents.length;
  const someSelected = selected.size > 0 && !allSelected;

  const deleteTitle = pendingDelete.length > 1
    ? t("torrent.confirmDeleteMany").replace("{count}", String(pendingDelete.length))
    : t("torrent.confirmDelete");

  return (
    <div className="bg-white dark:bg-stone-800 border border-blue-100 dark:border-blue-900 rounded-2xl overflow-hidden shadow-sm">
      {selected.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 dark:bg-blue-950 border-b border-blue-100 dark:border-blue-900">
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">{selected.size} {t("torrent.selected")}</span>
          <button
            onClick={pauseSelected}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40 hover:bg-amber-200 dark:hover:bg-amber-800/40 transition-colors"
          >
            <Pause size={12} />
            {t("torrent.pause")}
          </button>
          <button
            onClick={() => setPendingDelete([...selected])}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
          >
            <Trash2 size={12} />
            {t("torrent.delete")}
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-blue-400 dark:text-blue-500 hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
          >
            {t("torrent.clear")}
          </button>
        </div>
      )}

      <div className="overflow-y-auto max-h-120">
        <table className="w-full text-sm table-fixed">
          <TableHead
            allSelected={allSelected}
            someSelected={someSelected}
            onToggleAll={toggleSelectAll}
            stopAllTorrents={stopAllTorrents}
          />
          <tbody>
            {sortedTorrents.map((torrent, index) => (
              <TableRow
                key={torrent.id}
                index={index}
                torrent={torrent}
                selected={selected.has(torrent.id)}
                onToggleSelect={toggleSelect}
                onPause={pauseTorrent}
                onResume={resumeTorrent}
                onAskDelete={(id) => setPendingDelete([id])}
                onUpdateStatus={updateTorrentStatus}
              />
            ))}
          </tbody>
        </table>
      </div>

      {pendingDelete.length > 0 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-stone-800 rounded-2xl shadow-2xl w-80 p-6">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">
              {deleteTitle}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">{t("torrent.undone")}</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPendingDelete([])}
                className="px-4 py-2 rounded-full text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/40 hover:bg-blue-100 dark:hover:bg-blue-800/60 transition-colors"
              >
                {t("torrent.cancel")}
              </button>
              <button
                onClick={() => { deleteTorrents(pendingDelete); setPendingDelete([]); }}
                className="px-4 py-2 rounded-full text-sm font-medium text-white bg-red-500 hover:bg-red-600 transition-colors"
              >
                {t("torrent.delete")}
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

const TableHead = ({ allSelected, someSelected, onToggleAll, stopAllTorrents }: TableHeadProps) => {
  const { t } = useLanguage();
  return (
  <thead>
    <tr className="bg-blue-50 dark:bg-blue-950/60 text-xs font-semibold text-blue-500 dark:text-blue-400 uppercase tracking-wide border-b border-blue-100 dark:border-blue-900">
      <th className="px-4 py-3" style={{ width: "2%" }}>
        <input
          type="checkbox"
          checked={allSelected}
          ref={(el) => { if (el) el.indeterminate = someSelected; }}
          onChange={onToggleAll}
          className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      </th>
      <th className="text-left px-4 py-3" style={{ width: "25%" }}>{t("table.name")}</th>
      <th className="text-left px-4 py-3" style={{ width: "10%" }}>{t("table.size")}</th>
      <th className="text-left px-4 py-3" style={{ width: "18%" }}>{t("table.progress")}</th>
      <th className="text-left px-4 py-3" style={{ width: "8%" }}>{t("table.speed")}</th>
      <th className="text-left px-4 py-3" style={{ width: "10%" }}>{t("table.eta")}</th>
      <th className="text-left px-4 py-3" style={{ width: "10%" }}>{t("table.status")}</th>
      <th className="text-left px-4 py-3" style={{ width: "8%" }}>{t("table.health")}</th>
      <th className="text-left px-4 py-3" style={{ width: "9%" }}>
         <button
          onClick={stopAllTorrents}
          className="flex items-center gap-1.5 rounded-full bg-red-50 dark:bg-red-900/30 px-3 py-1.5 text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
        >
          <Pause size={12} />
          {t("torrent.stopAll")}
        </button>
      </th>
   
    </tr>
  </thead>
  );
};

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
  onUpdateStatus: (id: number, status: Torrent["status"]) => void;
};

const TableRow = ({ index, torrent, selected, onToggleSelect, onPause, onResume, onAskDelete, onUpdateStatus }: TableRowProps) => {
  const { t } = useLanguage();
  const [isEditing, setIsEditing] = useState(false);
  return (
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

    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
      {formatEstimatedTime(torrent)}
    </td>

    <td className="px-4 py-3">
      {isEditing ? (
        <select
          autoFocus
          value={torrent.status}
          onChange={(event) => {
            onUpdateStatus(torrent.id, event.target.value as Torrent["status"]);
            setIsEditing(false);
          }}
          onBlur={() => setIsEditing(false)}
          className="w-full rounded-full border border-blue-200 dark:border-blue-700 bg-white dark:bg-stone-800 text-xs font-medium px-2.5 py-1 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {editableStatuses.map((status) => (
            <option key={status} value={status}>{t(`status.${status.toLowerCase()}`)}</option>
          ))}
        </select>
      ) : torrent.status === "Completed" ? (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[torrent.status]}`}>
          {t(`status.${torrent.status.toLowerCase()}`)}
        </span>
      ) : (
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[torrent.status]} hover:ring-1 hover:ring-blue-300 dark:hover:ring-blue-800 transition-all`}
        >
          {t(`status.${torrent.status.toLowerCase()}`)}
        </button>
      )}
    </td>

    <td className="px-4 py-3">
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${healthStyles[torrent.health] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"}`}>
        {t(`health.${torrent.health.toLowerCase()}`)}
      </span>
    </td>

    <td className="px-4 py-3">
      <div className="flex items-center gap-1">
        {(torrent.status === "Downloading" || torrent.status === "Seeding") && (
          <button
            onClick={() => onPause(torrent.id)}
            title={t("torrent.pause")}
            className="p-1.5 rounded-full text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors"
          >
            <Pause size={15} />
          </button>
        )}
        {torrent.status === "Paused" && (
          <button
            onClick={() => onResume(torrent.id)}
            title={t("torrent.resume")}
            className="p-1.5 rounded-full text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
          >
            <Play size={15} />
          </button>
        )}
        <button
          onClick={() => onAskDelete(torrent.id)}
          title={t("torrent.delete")}
          className="p-1.5 rounded-full text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </td>
    <td />
  </tr>
  );
};
