import { useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { FileUp, FolderOpen, Link, X } from "lucide-react";
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
  const [torrentFilePath, setTorrentFilePath] = useState("");
  const [downloadPath, setDownloadPath] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const magnetValid = magnetUri.trim().startsWith("magnet:?");
  // TODO: backend has no magnet-link endpoint yet — only add-by-file-path is wired up
  const canSubmit = !submitting && tab === "file" && torrentFilePath.trim() !== "" && downloadPath.trim() !== "";

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    await addTorrent(torrentFilePath.trim(), downloadPath.trim());
    showToast("Torrent added");
    closeAddDialog();
  };

  const browseTorrentFile = async () => {
    const path = await open({
      multiple: false,
      filters: [{ name: "Torrent files", extensions: ["torrent"] }],
    });
    if (typeof path === "string") setTorrentFilePath(path);
  };

  const browseDownloadFolder = async () => {
    const path = await open({ directory: true, multiple: false });
    if (typeof path === "string") setDownloadPath(path);
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
              placeholder="magnet:?xt=..."
              disabled
              className="w-full text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-3 py-2.5 bg-white dark:bg-stone-700 text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            {magnetUri.trim() !== "" && !magnetValid && (
              <p className="text-xs text-red-500 dark:text-red-400">Must be a valid magnet link (magnet:?...)</p>
            )}
            <p className="text-xs text-stone-500 dark:text-stone-400">Magnet links aren't supported by the backend yet — use the Torrent File tab.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-stone-600 dark:text-stone-400">Torrent file path</label>
              <div className="flex gap-1.5">
                <input
                  autoFocus
                  type="text"
                  value={torrentFilePath}
                  onChange={(e) => setTorrentFilePath(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
                  placeholder="C:\path\to\file.torrent"
                  className="flex-1 min-w-0 text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-3 py-2.5 bg-white dark:bg-stone-700 text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={browseTorrentFile}
                  title="Browse for a .torrent file"
                  className="shrink-0 flex items-center gap-1.5 px-3 rounded-lg text-sm border border-blue-200 dark:border-blue-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                >
                  <FileUp size={14} />
                  Browse
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-stone-600 dark:text-stone-400">Download folder</label>
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={downloadPath}
                  onChange={(e) => setDownloadPath(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
                  placeholder="C:\Downloads"
                  className="flex-1 min-w-0 text-sm border border-blue-200 dark:border-blue-700 rounded-lg px-3 py-2.5 bg-white dark:bg-stone-700 text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={browseDownloadFolder}
                  title="Browse for a download folder"
                  className="shrink-0 flex items-center gap-1.5 px-3 rounded-lg text-sm border border-blue-200 dark:border-blue-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                >
                  <FolderOpen size={14} />
                  Browse
                </button>
              </div>
            </div>
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
