import React from "react";
import {
  Plus,
  Link,
  Download,
  Upload,
  Activity,
  Share2,
  FileDown,
} from "lucide-react";

const stats = [
  { label: "Download", value: "1.8 MB/s", icon: <Download className="w-5 h-5" /> },
  { label: "Upload", value: "0.3 MB/s", icon: <Upload className="w-5 h-5" /> },
  { label: "Active", value: "3", icon: <Activity className="w-5 h-5" /> },
  { label: "Seeding", value: "2", icon: <Share2 className="w-5 h-5" /> },
];

const recentTorrents = [
  { id: 1, name: "ubuntu.iso", size: "2.5 GB", status: "Completed" },
  { id: 2, name: "movie.mp4", size: "1.2 GB", status: "Paused" },
  { id: 3, name: "linux_tools.tar.gz", size: "4.7 GB", status: "Downloading" },
];

export const HomePage = () => {
  return (
    <div className="w-full min-h-screen bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-800 dark:text-stone-100">Home</h1>
          <p className="text-sm text-stone-500 dark:text-stone-400 mt-1">
            Overview of your torrent activity
          </p>
        </div>

        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm shadow-sm transition">
            <Plus size={16} />
            Add Torrent
          </button>

          <button className="flex items-center gap-2 px-3 py-2 border border-blue-200 dark:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/40 text-stone-600 dark:text-stone-300 rounded-md text-sm transition">
            <Link size={16} />
            Magnet
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-stone-500 dark:text-stone-400">{stat.label}</p>
              <div className="h-9 w-9 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                {stat.icon}
              </div>
            </div>
            <p className="text-xl font-bold text-stone-800 dark:text-stone-100 mt-2">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      <div className="w-full border border-blue-200 dark:border-blue-800 rounded-xl overflow-hidden shadow-sm bg-white dark:bg-stone-800">
        <div className="px-4 py-3 border-b border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/60 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-blue-800 dark:text-blue-300 flex items-center gap-2">
            <FileDown className="w-4 h-4" />
            Recent Torrents
          </h2>
          <span className="text-xs text-stone-500 dark:text-stone-400">
            {recentTorrents.length} items
          </span>
        </div>

        <table className="w-full text-sm">
          <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
            <tr className="text-left text-stone-500 dark:text-stone-400">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Size</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {recentTorrents.map((torrent, index) => (
              <tr
                key={torrent.id}
                className={`border-b border-blue-50 dark:border-blue-900/50 last:border-b-0 transition ${
                  index % 2 === 1 ? "bg-blue-50/40 dark:bg-blue-900/10" : "bg-white dark:bg-stone-800"
                } hover:bg-blue-50 dark:hover:bg-blue-900/20`}
              >
                <td className="px-4 py-4 font-medium text-stone-800 dark:text-stone-100">
                  {torrent.name}
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300">
                  {torrent.size}
                </td>
                <td className="px-4 py-4">
                  <span className="inline-flex rounded-full bg-blue-100 dark:bg-blue-900/40 px-2.5 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
                    {torrent.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
