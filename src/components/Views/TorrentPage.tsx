import { useEffect, useState } from "react";
import { FileDown, Users, Gauge, Radio } from "lucide-react";
import DataTable from "../UI/DataTable";
import { tableRowCls, thCls } from "../UI/tableStyles";
import EmptyState from "../UI/EmptyState";
import IconBox from "../UI/IconBox";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import * as torrentService from "../../services/torrentService";
import type { TorrentDetail, TorrentPageStats } from "../../services/types";

export const TorrentPage = () => {
  const [details, setDetails] = useState<TorrentDetail[]>([]);
  const [pageStats, setPageStats] = useState<TorrentPageStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    torrentService.getTorrentDetails().then((rows) => {
      setDetails(rows);
      setLoading(false);
    });
    torrentService.getTorrentPageStats().then(setPageStats);
  }, []);

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader title="Torrents" subtitle="Monitor torrent files, peers, trackers, and speed" />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Total Torrents" value={details.length} />
        <StatCard
          label="Active Peers"
          value={pageStats ? pageStats.totalPeers : "—"}
          valueClassName="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          label="Current Speed"
          value={pageStats ? pageStats.currentSpeed : "—"}
          valueClassName="text-green-600 dark:text-green-400"
        />
      </div>

      <DataTable
        icon={<FileDown className="w-4 h-4" />}
        title="Torrent List"
        count={details.length}
        countLabel="items"
        emptyState={
          <EmptyState
            icon={<FileDown size={28} />}
            title={loading ? "Loading…" : "No torrents yet"}
          />
        }
      >
        <thead className="bg-white dark:bg-stone-800 border-b border-blue-100 dark:border-blue-900">
          <tr className="text-start text-stone-500 dark:text-stone-400">
            <th className={thCls}>Files</th>
            <th className={thCls}>Info</th>
            <th className={`${thCls} hidden md:table-cell`}>Active Peers</th>
            <th className={`${thCls} hidden md:table-cell`}>Trackers</th>
            <th className={thCls}>Speed</th>
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
              <td className="px-4 py-4 text-stone-600 dark:text-stone-300 hidden md:table-cell">
                <span className="inline-flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-stone-400 dark:text-stone-500" />
                  {row.peers}
                </span>
              </td>
              <td className="px-4 py-4 text-stone-600 dark:text-stone-300 hidden md:table-cell">
                <span className="inline-flex items-center gap-1.5">
                  <Radio className="w-4 h-4 text-stone-400 dark:text-stone-500" />
                  {row.trackers}
                </span>
              </td>
              <td className="px-4 py-4 font-medium text-stone-800 dark:text-stone-100">
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
