import React from "react";
import { FileDown, Users, Gauge, Radio } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";

const tableData = [
  { id: 0, files: "ubuntu.iso",       info: "75% Downloaded", peers: "45 peers", trackers: "tracker.ubuntu.com", speed: "1.8 MB/s" },
  { id: 1, files: "movie.mp4",        info: "Paused",         peers: "12 peers", trackers: "tracker.movie.net",  speed: "0 MB/s"   },
  { id: 2, files: "game.zip",         info: "Seeding",        peers: "80 peers", trackers: "tracker.game.org",   speed: "0.3 MB/s" },
  { id: 3, files: "music_album.flac", info: "80% Downloaded", peers: "30 peers", trackers: "tracker.music.com",  speed: "2.4 MB/s" },
];

export const TorrentPage = () => {
  const { t } = useLanguage();

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-800 dark:text-stone-100">{t("torrents.title")}</h1>
        <p className="text-sm text-stone-500 dark:text-stone-400 mt-1">
          {t("torrents.subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-stone-500 dark:text-stone-400">{t("torrents.total")}</p>
          <p className="text-xl font-bold text-stone-800 dark:text-stone-100">{tableData.length}</p>
        </div>
        <div className="bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-stone-500 dark:text-stone-400">{t("torrents.peers")}</p>
          <p className="text-xl font-bold text-blue-600 dark:text-blue-400">167</p>
        </div>
        <div className="bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-stone-500 dark:text-stone-400">{t("torrents.speed")}</p>
          <p className="text-xl font-bold text-green-600 dark:text-green-400">4.5 MB/s</p>
        </div>
      </div>

      <div className="w-full border border-blue-200 dark:border-blue-800 rounded-xl overflow-hidden shadow-sm bg-white dark:bg-stone-800">
        <div className="px-4 py-3 border-b border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/60 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-blue-800 dark:text-blue-300 flex items-center gap-2">
            <FileDown className="w-4 h-4" />
            {t("torrents.list")}
          </h2>
          <span className="text-xs text-stone-500 dark:text-stone-400">{tableData.length} {t("common.items")}</span>
        </div>

        <div className="overflow-y-auto max-h-80">
          <table className="w-full text-sm">
          <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
            <tr className="text-left text-stone-500 dark:text-stone-400">
              <th className="px-4 py-3 font-medium">{t("torrents.files")}</th>
              <th className="px-4 py-3 font-medium">{t("torrents.info")}</th>
              <th className="px-4 py-3 font-medium">{t("torrents.peers")}</th>
              <th className="px-4 py-3 font-medium">{t("torrents.trackers")}</th>
              <th className="px-4 py-3 font-medium text-right">{t("table.speed")}</th>
            </tr>
          </thead>

          <tbody>
            {tableData.map((row, index) => (
              <tr
                key={row.id}
                className={`border-b border-blue-50 dark:border-blue-900/50 last:border-b-0 transition ${
                  index % 2 === 1 ? "bg-blue-50/40 dark:bg-blue-900/10" : "bg-white dark:bg-stone-800"
                } hover:bg-blue-50 dark:hover:bg-blue-900/20`}
              >
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                      <FileDown className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-medium text-stone-800 dark:text-stone-100">{row.files}</div>
                      <div className="text-xs text-stone-400 dark:text-stone-500">ID #{row.id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <span className="inline-flex rounded-full bg-blue-100 dark:bg-blue-900/40 px-2.5 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
                    {row.info}
                  </span>
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300">
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="w-4 h-4 text-stone-400 dark:text-stone-500" />
                    {row.peers}
                  </span>
                </td>
                <td className="px-4 py-4 text-stone-600 dark:text-stone-300">
                  <span className="inline-flex items-center gap-1.5">
                    <Radio className="w-4 h-4 text-stone-400 dark:text-stone-500" />
                    {row.trackers}
                  </span>
                </td>
                <td className="px-4 py-4 text-right font-medium text-stone-800 dark:text-stone-100">
                  <span className="inline-flex items-center gap-1.5">
                    <Gauge className="w-4 h-4 text-green-500 dark:text-green-400" />
                    {row.speed}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
