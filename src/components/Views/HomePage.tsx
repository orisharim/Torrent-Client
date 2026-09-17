import { useEffect, useState } from "react";
import { Plus, Link, Download, Upload, Activity, Share2 } from "lucide-react";
import Button from "../UI/Button";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useUI } from "../../context/UIContext";
import * as statsService from "../../services/statsService";
import type { HomeStats } from "../../services/types";

export const HomePage = () => {
  const { openAddDialog } = useUI();
  const [homeStats, setHomeStats] = useState<HomeStats | null>(null);

  useEffect(() => {
    statsService.getHomeStats().then(setHomeStats);
  }, []);

  const stats = homeStats
    ? [
        { label: "Download", value: homeStats.downloadSpeed,           icon: <Download className="w-5 h-5" /> },
        { label: "Upload",   value: homeStats.uploadSpeed,             icon: <Upload className="w-5 h-5" />   },
        { label: "Active",   value: homeStats.activeTorrents,          icon: <Activity className="w-5 h-5" /> },
        { label: "Seeding",  value: homeStats.seedingTorrents,         icon: <Share2 className="w-5 h-5" />   },
      ]
    : [];

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader
        title="Home"
        subtitle="Overview of your torrent activity"
        actions={
          <>
            <Button text="Add Torrent" icon={<Plus size={16} />} action={() => openAddDialog("magnet")} variant="primary" />
            <Button text="Magnet" icon={<Link size={16} />} action={() => openAddDialog("magnet")} />
          </>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {homeStats
          ? stats.map((stat) => (
              <StatCard key={stat.label} label={stat.label} value={stat.value} icon={stat.icon} />
            ))
          : Array.from({ length: 4 }, (_, index) => (
              <div
                key={index}
                className="h-24 rounded-xl border border-blue-100 dark:border-blue-900 bg-white dark:bg-stone-800 animate-pulse"
              />
            ))}
      </div>
    </div>
  );
};
