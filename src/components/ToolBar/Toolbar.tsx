import {
  Plus,
  Link,
  Square,
  Trash2,
  Search,
  Sun,
  Moon,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../../context/LanguageContext";
import { useTheme } from "../../context/ThemeContext";
import { useTorrents } from "../../context/TorrentContext";
import { useUI } from "../../context/UIContext";
import ConfirmDialog from "../UI/ConfirmDialog";

const Toolbar = () => {
  const { t } = useLanguage();
  const { theme, setTheme } = useTheme();
  const { torrents, selected, pauseAll, deleteTorrents } = useTorrents();
  const { filterText, setFilterText, submitSearch, openAddDialog, showToast } = useUI();

  const [confirmRemove, setConfirmRemove] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const hasDownloading = torrents.some((torrent) => torrent.status === "Downloading");

  // Ctrl+F or "/" focuses the search box
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName);
      if ((event.ctrlKey && event.key.toLowerCase() === "f") || (event.key === "/" && !typing)) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const toggleTheme = () => {
    setTheme(theme === "Dark" ? "Light" : "Dark");
  };

  const handleStopAll = () => {
    pauseAll();
    showToast(t("torrent.stopAll"));
  };

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && filterText.trim() !== "") {
      submitSearch(filterText.trim());
    } else if (event.key === "Escape") {
      setFilterText("");
      searchRef.current?.blur();
    }
  };

  return (
    <div className="sticky top-0 z-40 w-full h-16 bg-blue-100 dark:bg-stone-900 border-b border-blue-200 dark:border-blue-900 px-4 py-2 flex flex-nowrap items-center gap-2">

      <button
        onClick={() => openAddDialog("magnet")}
        className="flex font-bold items-center gap-2 px-3 py-2 text-sm transition text-stone-800 dark:text-stone-200 hover:bg-blue-200 dark:hover:bg-blue-900 rounded"
      >
        <Plus size={20} className="font-bold" />
        <span className="hidden sm:inline">{t("toolbar.addTorrent")}</span>
      </button>

      <ToolbarButton
        icon={<Link size={16} />}
        label={t("toolbar.magnet")}
        onClick={() => openAddDialog("magnet")}
      />

      <Divider />

      <ToolbarButton
        icon={<Square size={16} />}
        label={t("toolbar.stop")}
        onClick={handleStopAll}
        disabled={!hasDownloading}
      />

      <ToolbarButton
        icon={<Trash2 size={16} />}
        label={t("toolbar.remove")}
        onClick={() => setConfirmRemove(true)}
        disabled={selected.size === 0}
        danger
      />

      <div className="ms-auto flex flex-nowrap items-center gap-2">
        <div className="min-w-0 flex items-center bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-md px-3 h-9 w-40 md:w-64 focus-within:ring-2 focus-within:ring-blue-400 transition-shadow">
          <Search className="w-4 h-4 shrink-0 text-stone-400 dark:text-stone-500 me-2" />
          <input
            ref={searchRef}
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder={t("toolbar.search")}
            title={t("toolbar.searchHint")}
            className="w-full min-w-0 text-sm bg-transparent outline-none text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500"
          />
          {filterText !== "" && (
            <button
              type="button"
              onClick={() => { setFilterText(""); searchRef.current?.focus(); }}
              className="shrink-0 p-0.5 rounded-full text-stone-400 dark:text-stone-500 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={toggleTheme}
          title={theme === "Dark" ? "Switch to light mode" : "Switch to dark mode"}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-blue-200 dark:border-blue-800 bg-white dark:bg-stone-800 text-stone-600 dark:text-stone-200 hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
        >
          {theme === "Dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>

      {confirmRemove && (
        <ConfirmDialog
          title={
            selected.size > 1
              ? t("torrent.confirmDeleteMany").replace("{count}", String(selected.size))
              : t("torrent.confirmDelete")
          }
          message={t("torrent.undone")}
          confirmLabel={t("torrent.delete")}
          cancelLabel={t("torrent.cancel")}
          onConfirm={() => { deleteTorrents([...selected]); setConfirmRemove(false); }}
          onCancel={() => setConfirmRemove(false)}
        />
      )}
    </div>
  );
};

export default Toolbar;

const ToolbarButton = ({
  icon,
  label,
  onClick,
  danger,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 px-3 py-2 text-sm transition rounded
        ${
          disabled
            ? "text-stone-400 dark:text-stone-600 cursor-not-allowed"
            : danger
            ? "text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
            : "text-stone-800 dark:text-stone-200 hover:bg-blue-200 dark:hover:bg-blue-900"
        }`}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
};

const Divider = () => (
  <div className="w-px h-6 bg-blue-300 dark:bg-blue-700 mx-1" />
);
