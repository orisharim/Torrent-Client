import { useMemo, useState } from "react";
import { Download, MoreVertical, Pause, Play, Trash2, X } from "lucide-react";
import { useTorrents, type Torrent } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
import EmptyState from "../ui/EmptyState";
import Modal from "../ui/Modal";

const statusPriority: Record<Torrent["status"], number> = {
  Downloading: 0,
  Seeding: 1,
  Paused: 2,
  Completed: 3,
};

const formatEstimatedTime = (torrent: Torrent) => {
  if (torrent.status !== "Downloading" || torrent.speed <= 0 || torrent.progress >= 100 || torrent.size <= 0) {
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
  const {
    torrents, loading,
    selected, setSelected, toggleSelect,
    pauseTorrent, resumeTorrent,
    deleteTorrents, setTorrentFlags,
  } = useTorrents();
  const { filterText, openAddDialog } = useUI();

  const [pendingDelete, setPendingDelete] = useState<string[]>([]);
  const [actionsFor, setActionsFor] = useState<Torrent | null>(null);

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
    ? `Delete ${pendingDelete.length} torrents?`
    : "Delete Torrent?";

  return (
    <div className="bg-white dark:bg-stone-800 border border-blue-100 dark:border-blue-900 rounded-2xl overflow-hidden shadow-sm">
      {loading ? (
        <EmptyState title="Loading…" />
      ) : torrents.length === 0 ? (
        <EmptyState
          icon={<Download size={28} />}
          title="No torrents yet"
          description="Click Add Torrent to get started"
          action={<Button text="Add Torrent" variant="primary" action={() => openAddDialog("magnet")} />}
        />
      ) : filtered.length === 0 ? (
        <EmptyState title={`No torrents match "${filterText.trim()}"`} />
      ) : (
        <div className="overflow-x-hidden">
          <table className="w-full text-sm table-fixed">
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
                  onSetFlags={setTorrentFlags}
                  onOpenActions={setActionsFor}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pendingDelete.length > 0 && (
        <ConfirmDialog
          title={deleteTitle}
          message="This action cannot be undone."
          confirmLabel="Delete"
          cancelLabel="Cancel"
          onConfirm={() => { deleteTorrents(pendingDelete); setPendingDelete([]); }}
          onCancel={() => setPendingDelete([])}
        />
      )}

      {actionsFor && (
        <ActionsModal
          torrent={actionsFor}
          onClose={() => setActionsFor(null)}
          onPause={() => { pauseTorrent(actionsFor.id); setActionsFor(null); }}
          onResume={() => { resumeTorrent(actionsFor.id); setActionsFor(null); }}
          onDelete={() => { setPendingDelete([actionsFor.id]); setActionsFor(null); }}
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

const TableHead = ({ allSelected, someSelected, onToggleAll }: TableHeadProps) => (
  <thead>
    <tr className="bg-blue-50 dark:bg-blue-950/60 text-xs font-semibold text-blue-500 dark:text-blue-400 uppercase tracking-wide border-b border-blue-100 dark:border-blue-900">
      <th className="px-4 py-3 w-12 align-middle">
        <input
          type="checkbox"
          checked={allSelected}
          ref={(el) => { if (el) el.indeterminate = someSelected; }}
          onChange={onToggleAll}
          className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      </th>
      <th className="text-start px-4 py-3 w-[22%]">Name</th>
      <th className="text-start px-4 py-3 w-[9%] whitespace-nowrap">Size</th>
      <th className="text-start px-4 py-3 w-[16%]">Progress</th>
      <th className="text-start px-4 py-3 w-[11%] whitespace-nowrap hidden sm:table-cell">Speed</th>
      <th className="text-start px-4 py-3 w-[9%] whitespace-nowrap hidden lg:table-cell">ETA</th>
      <th className="px-3 py-3 w-[12%] whitespace-nowrap text-center">Downloading</th>
      <th className="px-3 py-3 w-[9%] whitespace-nowrap text-center">Seeding</th>
      <th className="text-center px-2 py-3 w-20">Actions</th>
    </tr>
  </thead>
);

type TableRowProps = {
  index: number;
  torrent: Torrent;
  selected: boolean;
  onToggleSelect: (id: string) => void;
  onSetFlags: (id: string, isDownloading: boolean, isSeeding: boolean) => void;
  onOpenActions: (torrent: Torrent) => void;
};

const TableRow = ({ index, torrent, selected, onToggleSelect, onSetFlags, onOpenActions }: TableRowProps) => {
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
    <td className="px-4 py-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">{torrent.size > 0 ? `${torrent.size.toFixed(2)} GB` : "—"}</td>

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
      {torrent.speed > 0 ? `${torrent.speed.toFixed(2)} MB/s` : "—"}
    </td>

    <td className="px-4 py-3 text-gray-600 dark:text-gray-300 whitespace-nowrap hidden lg:table-cell">
      {formatEstimatedTime(torrent)}
    </td>

    <td className="px-3 py-3 text-center">
      <input
        type="checkbox"
        checked={torrent.isDownloading}
        onChange={(event) => onSetFlags(torrent.id, event.target.checked, torrent.isSeeding)}
        title="Downloading"
        className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
      />
    </td>

    <td className="px-3 py-3 text-center">
      <input
        type="checkbox"
        checked={torrent.isSeeding}
        onChange={(event) => onSetFlags(torrent.id, torrent.isDownloading, event.target.checked)}
        title="Seeding"
        className="rounded border-blue-300 dark:border-blue-600 text-blue-600 focus:ring-blue-500 cursor-pointer"
      />
    </td>

    <td className="px-2 py-3 text-center">
      <button
        onClick={() => onOpenActions(torrent)}
        title="Actions"
        className="p-1.5 rounded-full text-stone-500 dark:text-stone-400 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
      >
        <MoreVertical size={16} />
      </button>
    </td>
  </tr>
  );
};

type ActionsModalProps = {
  torrent: Torrent;
  onClose: () => void;
  onPause: () => void;
  onResume: () => void;
  onDelete: () => void;
};

const ActionsModal = ({ torrent, onClose, onPause, onResume, onDelete }: ActionsModalProps) => {
  const canPause = torrent.status === "Downloading" || torrent.status === "Seeding";
  const canResume = torrent.status === "Paused";

  return (
    <Modal onClose={onClose} widthCls="max-w-xs" panelCls="bg-white dark:bg-stone-800">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-blue-100 dark:border-blue-900">
        <span className="font-medium text-sm text-stone-800 dark:text-stone-100 truncate" title={torrent.name}>
          {torrent.name}
        </span>
        <button
          onClick={onClose}
          className="shrink-0 p-1 rounded-full text-stone-400 dark:text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
        >
          <X size={16} />
        </button>
      </div>
      <div className="p-2 flex flex-col gap-1">
        {canPause && (
          <button
            onClick={onPause}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/30 transition-colors"
          >
            <Pause size={16} /> Pause
          </button>
        )}
        {canResume && (
          <button
            onClick={onResume}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
          >
            <Play size={16} /> Resume
          </button>
        )}
        <button
          onClick={onDelete}
          className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
        >
          <Trash2 size={16} /> Delete
        </button>
      </div>
    </Modal>
  );
};
