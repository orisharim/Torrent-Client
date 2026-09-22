import { Plus, Link, Download, Upload, Activity, Share2 } from "lucide-react";
import Button from "../UI/Button";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useUI } from "../../context/UIContext";
import { useTorrents } from "../../context/TorrentContext";

export const HomePage = () => {
  const { openAddDialog } = useUI();
  const { torrents, loading } = useTorrents();

  const activeTorrents = torrents.filter((t) => t.status === "Downloading").length;
  const seedingTorrents = torrents.filter((t) => t.status === "Seeding").length;
  const downloadSpeed = torrents
    .filter((t) => t.status === "Downloading")
    .reduce((sum, t) => sum + t.speed, 0);

  // TODO: backend doesn't report an upload speed anywhere in the torrent status payload yet — always 0 until it does
  const uploadSpeed = 0;

  const stats = [
    { label: "Download", value: `${downloadSpeed.toFixed(1)} MB/s`, icon: <Download className="w-5 h-5" /> },
    { label: "Upload", value: `${uploadSpeed.toFixed(1)} MB/s`, icon: <Upload className="w-5 h-5" /> },
    { label: "Active", value: activeTorrents, icon: <Activity className="w-5 h-5" /> },
    { label: "Seeding", value: seedingTorrents, icon: <Share2 className="w-5 h-5" /> },
  ];

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
        {loading
          ? Array.from({ length: 4 }, (_, index) => (
              <div
                key={index}
                className="h-24 rounded-xl border border-blue-100 dark:border-blue-900 bg-white dark:bg-stone-800 animate-pulse"
              />
            ))
          : stats.map((stat) => (
              <StatCard key={stat.label} label={stat.label} value={stat.value} icon={stat.icon} />
            ))}
      </div>
    </div>
  );
};
