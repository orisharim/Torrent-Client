import { FileDown, Users, Gauge } from "lucide-react";
import DataTable from "../UI/DataTable";
import { tableRowCls, thCls } from "../UI/tableStyles";
import EmptyState from "../UI/EmptyState";
import IconBox from "../UI/IconBox";
import PageHeader from "../UI/PageHeader";
import StatCard from "../UI/StatCard";
import { useTorrents } from "../../context/TorrentContext";

export const TorrentPage = () => {
  const { torrents, loading } = useTorrents();

  const totalPeers = torrents.reduce((sum, t) => sum + t.peers, 0);
  const currentSpeed = torrents
    .filter((t) => t.status === "Downloading")
    .reduce((sum, t) => sum + t.speed, 0);

  return (
    <div className="w-full bg-stone-50 dark:bg-stone-900 p-6 flex flex-col gap-6">
      <PageHeader title="Torrents" subtitle="Monitor torrent files, peers, and speed" />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Total Torrents" value={torrents.length} />
        <StatCard
          label="Active Peers"
          value={totalPeers}
          valueClassName="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          label="Current Speed"
          value={`${currentSpeed.toFixed(1)} MB/s`}
          valueClassName="text-green-600 dark:text-green-400"
        />
      </div>

      <DataTable
        icon={<FileDown className="w-4 h-4" />}
        title="Torrent List"
        count={torrents.length}
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
            <th className={`${thCls} hidden md:table-cell`}>Active Peers</th>
            <th className={thCls}>Speed</th>
          </tr>
        </thead>
        <tbody>
          {torrents.map((torrent, index) => (
            <tr key={torrent.id} className={tableRowCls(index)}>
              <td className="px-4 py-4">
                <div className="flex items-center gap-3">
                  <IconBox icon={<FileDown className="w-5 h-5" />} />
                  <div>
                    <div className="font-medium text-stone-800 dark:text-stone-100">{torrent.name}</div>
                    <div className="text-xs text-stone-400 dark:text-stone-500">{torrent.status}</div>
                  </div>
                </div>
              </td>
              <td className="px-4 py-4 text-stone-600 dark:text-stone-300 hidden md:table-cell">
                <span className="inline-flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-stone-400 dark:text-stone-500" />
                  {torrent.peers}
                </span>
              </td>
              <td className="px-4 py-4 font-medium text-stone-800 dark:text-stone-100">
                <span className="inline-flex items-center gap-1.5">
                  <Gauge className="w-4 h-4 text-green-500 dark:text-green-400" />
                  {torrent.speed > 0 ? `${torrent.speed} MB/s` : "—"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
};
