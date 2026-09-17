import { useRef, useState } from "react";
import { FileUp, Link, X } from "lucide-react";
import Modal from "../UI/Modal";
import Button from "../UI/Button";
import { useTorrents } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import type { AddDialogTab } from "../../context/UIContext";

export const AddTorrentDialog = () => {
  const { addTorrent } = useTorrents();
  const { addDialog, closeAddDialog, showToast } = useUI();

  const [tab, setTab] = useState<AddDialogTab>(addDialog.tab);
  const [magnetUri, setMagnetUri] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const magnetValid = magnetUri.trim().startsWith("magnet:?");
  const canSubmit = !submitting && (tab === "magnet" ? magnetValid : file !== null);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    // REPLACE: for files, read bytes / use tauri-plugin-dialog for a real filesystem path
    // once a torrent engine consumes the .torrent contents
    await addTorrent(
      tab === "magnet"
        ? { type: "magnet", uri: magnetUri.trim() }
        : { type: "file", fileName: file!.name }
    );
    showToast("Torrent added");
    closeAddDialog();
  };

  const tabCls = (active: boolean) =>
    `flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
      active
        ? "bg-blue-600 text-white shadow-md"
        : "text-blue-500 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/40"
    }`;

  return (
    <Modal onClose={closeAddDialog} widthCls="max-w-md">
      <div className="p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Add Torrent</h2>
          <button
            onClick={closeAddDialog}
            className="p-1.5 rounded-full text-stone-400 dark:text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex items-center gap-1 bg-blue-50 dark:bg-blue-950 rounded-full p-1 w-fit">
          <button type="button" onClick={() => setTab("magnet")} className={tabCls(tab === "magnet")}>
            <Link size={14} />
            Magnet Link
          </button>
          <button type="button" onClick={() => setTab("file")} className={tabCls(tab === "file")}>
            <FileUp size={14} />
            Torrent File
          </button>
        </div>

        {tab === "magnet" ? (
          <div className="flex flex-col gap-1.5">
            <input
              autoFocus
              type="text"
              value={magnetUri}
              onChange={(e) => setMagnetUri(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
              placeholder="magnet:?xt=..."
              className="w-full text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-3 py-2.5 bg-white dark:bg-stone-700 text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {magnetUri.trim() !== "" && !magnetValid && (
              <p className="text-xs text-red-500 dark:text-red-400">Must be a valid magnet link (magnet:?...)</p>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            <input
              ref={fileInputRef}
              type="file"
              accept=".torrent"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-blue-200 dark:border-blue-800 rounded-xl py-8 px-4 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
            >
              <FileUp size={22} />
              Choose a .torrent file
            </button>
            <p className="text-xs text-stone-500 dark:text-stone-400 text-center truncate" title={file?.name}>
              {file ? file.name : "No file selected"}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button text="Cancel" action={closeAddDialog} />
          <Button text="Add" action={handleSubmit} variant="primary" disabled={!canSubmit} />
        </div>
      </div>
    </Modal>
  );
};
