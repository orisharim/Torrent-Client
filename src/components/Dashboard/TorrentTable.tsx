import { useMemo, useState } from "react";
import { Download, Pause, Play, Trash2 } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";
import { useTorrents, type Torrent } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import { healthStyles, statusStyles } from "../UI/badgeStyles";
import Button from "../UI/Button";
import ConfirmDialog from "../UI/ConfirmDialog";
import EmptyState from "../UI/EmptyState";

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
  const {
    torrents, loading,
    selected, setSelected, toggleSelect,
    pauseTorrent, resumeTorrent, pauseSelected,
    deleteTorrents, updateTorrentStatus,
  } = useTorrents();
  const { filterText, openAddDialog } = useUI();

  const [pendingDelete, setPendingDelete] = useState<number[]>([]);

  const filtered = useMemo(() => {
    const query = filterText.trim().toLowerCase();
    const matching = query === "" ? torrents : torrents.filter((torrent) => torrent.name.toLowerCase().includes(query));
    return [...matching].sort((a, b) => statusPriority[a.status] - statusPriority[b.status]);
  }, [torrents, filterText]);

  const allSelected = filtered.length > 0 && filtered.every((torrent) => selected.has(torrent.id));
  const someSelected = selected.size > 0 && !allSelected;

  const toggleSelectAll = () => {
    setSelected(allSelected ? new Set() : new Set(filtered.map((torrent) => torrent.id)));
  };

  const deleteTitle = pendingDelete.length > 1
    ? t("torrent.confirmDeleteMany").replace("{count}", String(pendingDelete.length))
    : t("torrent.confirmDelete");

  return (
    <div className="bg-white dark:bg-stone-800 border border-blue-100 dark:border-blue-900 rounded-2xl overflow-hidden shadow-sm">
      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-blue-50 dark:bg-blue-950 border-b border-blue-100 dark:border-blue-900">
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
            className="ms-auto text-xs text-blue-400 dark:text-blue-500 hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
          >
            {t("torrent.clear")}
          </button>
        </div>
      )}

      {loading ? (
        <EmptyState title={t("empty.loading")} />
      ) : torrents.length === 0 ? (
        <EmptyState
          icon={<Download size={28} />}
          title={t("empty.noTorrents")}
          description={t("empty.noTorrentsSub")}
          action={<Button text={t("toolbar.addTorrent")} variant="primary" action={() => openAddDialog("magnet")} />}
        />
      ) : filtered.length === 0 ? (
        <EmptyState title={t("empty.noMatches").replace("{query}", filterText.trim())} />
      ) : (
        <div className="overflow-y-auto overflow-x-auto max-h-[40vh]">
          <table className="w-full text-sm">
            <TableHead
              allSelected={allSelected}
              someSelected={someSelected}
              onToggleAll={toggleSelectAll}
            />
            <tbody>
              {filtered.map((torrent, index) => (
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
      )}

      {pendingDelete.length > 0 && (
        <ConfirmDialog
          title={deleteTitle}
          message={t("torrent.undone")}
          confirmLabel={t("torrent.delete")}
          cancelLabel={t("torrent.cancel")}
          onConfirm={() => { deleteTorrents(pendingDelete); setPendingDelete([]); }}
          onCancel={() => setPendingDelete([])}
        />
      )}
    </div>
  );
};

type TableHeadProps = {
  allSelected: boolean;
  someSelected: boolean;
  onToggleAll: () => void;
};

const TableHead = ({ allSelected, someSelected, onToggleAll }: TableHeadProps) => {
  const { t } = useLanguage();
  return (
  <thead>
    <tr className="bg-blue-50 dark:bg-blue-950/60 text-xs font-semibold text-blue-500 dark:text-blue-400 uppercase tracking-wide border-b border-blue-100 dark:border-blue-900">
      <th className="px-4 py-3 w-10">
        <input
          type="checkbox"
          checked={allSelected}
          ref={(el) => { if (el) el.indeterminate = someSelected; }}
          onChange={onToggleAll}
          className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      </th>
      <th className="text-start px-4 py-3">{t("table.name")}</th>
      <th className="text-start px-4 py-3 whitespace-nowrap">{t("table.size")}</th>
      <th className="text-start px-4 py-3 min-w-32">{t("table.progress")}</th>
      <th className="text-start px-4 py-3 whitespace-nowrap hidden sm:table-cell">{t("table.speed")}</th>
      <th className="text-start px-4 py-3 whitespace-nowrap hidden lg:table-cell">{t("table.eta")}</th>
      <th className="text-start px-4 py-3">{t("table.status")}</th>
      <th className="text-start px-4 py-3 hidden lg:table-cell">{t("table.health")}</th>
      <th className="text-start px-4 py-3">{t("table.actions")}</th>
    </tr>
  </thead>
  );
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

    <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-100">
      <div className="max-w-64 truncate" title={torrent.name}>{torrent.name}</div>
    </td>
    <td className="px-4 py-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">{torrent.size} GB</td>

    <td className="px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-16 bg-blue-100 dark:bg-blue-900/40 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-500 h-full rounded-full transition-all duration-500"
            style={{ width: `${torrent.progress}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 w-8 text-end">{Math.round(torrent.progress)}%</span>
      </div>
    </td>

    <td className="px-4 py-3 text-gray-600 dark:text-gray-300 whitespace-nowrap hidden sm:table-cell">
      {torrent.speed > 0 ? `${torrent.speed} MB/s` : "—"}
    </td>

    <td className="px-4 py-3 text-gray-600 dark:text-gray-300 whitespace-nowrap hidden lg:table-cell">
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

    <td className="px-4 py-3 hidden lg:table-cell">
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
  </tr>
  );
};
