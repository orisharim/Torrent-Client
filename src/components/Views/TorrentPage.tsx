import React, { useEffect, useState } from "react";
import { FileDown, Users, Gauge, Radio } from "lucide-react";
import DataTable, { tableRowCls, thCls } from "../UI/DataTable";
import IconBox from "../UI/IconBox";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useLanguage } from "../../context/LanguageContext";
import * as torrentService from "../../services/torrentService";
import type { TorrentDetail, TorrentPageStats } from "../../services/types";

export const TorrentPage = () => {
  const { t } = useLanguage();
  const [details, setDetails] = useState<TorrentDetail[]>([]);
  const [pageStats, setPageStats] = useState<TorrentPageStats | null>(null);

  useEffect(() => {
    torrentService.getTorrentDetails().then(setDetails);
    torrentService.getTorrentPageStats().then(setPageStats);
  }, []);

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader title={t("torrents.title")} subtitle={t("torrents.subtitle")} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label={t("torrents.total")} value={details.length} />
        <StatCard
          label={t("torrents.peers")}
          value={pageStats ? pageStats.totalPeers : "—"}
          valueClassName="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          label={t("torrents.speed")}
          value={pageStats ? pageStats.currentSpeed : "—"}
          valueClassName="text-green-600 dark:text-green-400"
        />
      </div>

      <DataTable
        icon={<FileDown className="w-4 h-4" />}
        title={t("torrents.list")}
        count={details.length}
        countLabel={t("common.items")}
      >
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-left text-stone-500 dark:text-stone-400">
            <th className={thCls}>{t("torrents.files")}</th>
            <th className={thCls}>{t("torrents.info")}</th>
            <th className={thCls}>{t("torrents.peers")}</th>
            <th className={thCls}>{t("torrents.trackers")}</th>
            <th className={`${thCls} text-right`}>{t("table.speed")}</th>
          </tr>
        </thead>
        <tbody>
          {details.map((row, index) => (
            <tr key={row.id} className={tableRowCls(index)}>
              <td className="px-4 py-4">
                <div className="flex items-center gap-3">
                  <IconBox icon={<FileDown className="w-5 h-5" />} />
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
      </DataTable>
    </div>
  );
};
