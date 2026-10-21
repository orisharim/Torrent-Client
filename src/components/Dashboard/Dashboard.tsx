import Toolbar from "../ToolBar/Toolbar";
import { HomePage } from "../Views/HomePage";
import { SettingsPage } from "../Views/SettingsPage";
import { TorrentTable } from "./TorrentTable";
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

      {page === "home" && <HomePage />}

      {page === "settings" && <SettingsPage onClose={() => setPage("home")} />}

      {addDialog.open && <AddTorrentDialog />}

      <ToastViewport />
    </div>
  );
};
