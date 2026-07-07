import Toolbar from "../ToolBar/Toolbar";
import { HomePage } from "../Views/HomePage";
import { TorrentPage } from "../Views/TorrentPage";
import { FeedsPage } from "../Views/FeedsPage";
import { DevicePage } from "../Views/DevicePage";
import { SettingsPage } from "../Views/SettingsPage";
import { SearchPage } from "../Views/SearchPage";
import { TorrentTable } from "./TorrentTable";
import Tabs from "./Tabs";
import { AddTorrentDialog } from "../Dialogs/AddTorrentDialog";
import { ToastViewport } from "../UI/Toast";
import { useUI } from "../../context/UIContext";

export const Dashboard = () => {
  const { page, setPage, addDialog } = useUI();

  return (
    <div className="bg-stone-50 dark:bg-stone-900 min-h-screen w-full">
      <Toolbar />

      <div className="px-4 mt-3">
        <TorrentTable />
      </div>

      <Tabs />

      {page === "home" && <HomePage />}

      {page === "torrent" && <TorrentPage />}

      {page === "network" && <FeedsPage />}

      {page === "devices" && <DevicePage />}

      {page === "search" && <SearchPage />}

      {page === "settings" && <SettingsPage onClose={() => setPage("home")} />}

      {addDialog.open && <AddTorrentDialog />}

      <ToastViewport />
    </div>
  );
};
