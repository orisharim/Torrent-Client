import React from "react";
import { Grid } from "./Grid";
import Toolbar from "../ToolBar/Toolbar";
import { HomePage } from "../Views/HomePage";
import { TorrentPage } from "../Views/TorrentPage";
import { FeedsPage } from "../Views/FeedsPage";
import { DevicePage } from "../Views/DevicePage";
import { SettingsPage } from "../Views/SettingsPage";
import Tabs from "../Sidebar/Tabs";

type DashboardProps = {
  page: string;
  setPage: React.Dispatch<React.SetStateAction<string>>;
};

export const Dashboard = ({ page, setPage }: DashboardProps) => {
  return (
    <div className="bg-stone-50 min-h-screen w-full">
      <Toolbar />

      <Grid />

      <Tabs setPage={setPage} page={page} />

      {page === "home" && <HomePage />}

      {page === "torrent" && <TorrentPage />}

      {page === "network" && <FeedsPage />}

      {page === "devices" && <DevicePage />}

      {page === "settings" && <SettingsPage />}
    </div>
  );
};