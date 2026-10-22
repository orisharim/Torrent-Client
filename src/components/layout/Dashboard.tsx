import Toolbar from "./Toolbar";
import { HomePage } from "../pages/HomePage";
import { SettingsPage } from "../pages/SettingsPage";
import { TorrentTable } from "../torrents/TorrentTable";
import { AddTorrentDialog } from "../torrents/AddTorrentDialog";
import { ToastViewport } from "../ui/Toast";
import { useUI } from "../../context/UIContext";

export const Dashboard = () => {
  const { page, setPage, addDialog } = useUI();

  return (
    <div className="bg-stone-50 dark:bg-stone-900 min-h-screen w-full">
      <Toolbar />

      <div className="px-4 mt-3">
        <TorrentTable />
      </div>

      {page === "home" && <HomePage />}

      {page === "settings" && <SettingsPage onClose={() => setPage("home")} />}

      {addDialog.open && <AddTorrentDialog />}

      <ToastViewport />
    </div>
  );
};
