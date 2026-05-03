import React from "react";
import { FileDown, Users, Gauge, Radio } from "lucide-react";

const tableData = [
  {
    id: 0,
    files: "ubuntu.iso",
    info: "75% Downloaded",
    peers: "45 peers",
    trackers: "tracker.ubuntu.com",
    speed: "1.8 MB/s",
  },
  {
    id: 1,
    files: "movie.mp4",
    info: "Paused",
    peers: "12 peers",
    trackers: "tracker.movie.net",
    speed: "0 MB/s",
  },
  {
    id: 2,
    files: "game.zip",
    info: "Seeding",
    peers: "80 peers",
    trackers: "tracker.game.org",
    speed: "0.3 MB/s",
  },
  {
    id: 3,
    files: "music_album.flac",
    info: "80% Downloaded",
    peers: "30 peers",
    trackers: "tracker.music.com",
    speed: "2.4 MB/s",
  },
];

export const TorrentPage = () => {
  return (
    <div className="w-full min-h-screen bg-stone-50 p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-800">Torrents</h1>
        <p className="text-sm text-stone-500 mt-1">
          Monitor torrent files, peers, trackers, and speed
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-blue-200 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-stone-500">Total Torrents</p>
          <p className="text-xl font-bold text-stone-800">{tableData.length}</p>
        </div>

        <div className="bg-white border border-blue-200 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-stone-500">Active Peers</p>
          <p className="text-xl font-bold text-blue-600">167</p>
        </div>

        <div className="bg-white border border-blue-200 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-stone-500">Current Speed</p>
          <p className="text-xl font-bold text-green-600">4.5 MB/s</p>
        </div>
      </div>

      <div className="w-full border border-blue-200 rounded-xl overflow-hidden shadow-sm bg-white">
        <div className="px-4 py-3 border-b border-blue-100 bg-blue-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-blue-800 flex items-center gap-2">
            <FileDown className="w-4 h-4" />
            Torrent List
          </h2>

          <span className="text-xs text-stone-500">
            {tableData.length} items
          </span>
        </div>

        <table className="w-full text-sm">
          <thead className="bg-white border-b border-blue-100">
            <tr className="text-left text-stone-500">
              <th className="px-4 py-3 font-medium">Files</th>
              <th className="px-4 py-3 font-medium">Info</th>
              <th className="px-4 py-3 font-medium">Peers</th>
              <th className="px-4 py-3 font-medium">Trackers</th>
              <th className="px-4 py-3 font-medium text-right">Speed</th>
            </tr>
          </thead>

          <tbody>
            {tableData.map((row, index) => (
              <tr
                key={row.id}
                className={`border-b border-blue-50 last:border-b-0 transition ${
                  index % 2 === 1 ? "bg-blue-50/40" : "bg-white"
                } hover:bg-blue-50`}
              >
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
                      <FileDown className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-medium text-stone-800">
                        {row.files}
                      </div>
                      <div className="text-xs text-stone-400">
                        ID #{row.id}
                      </div>
                    </div>
                  </div>
                </td>

                <td className="px-4 py-4">
                  <span className="inline-flex rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700">
                    {row.info}
                  </span>
                </td>

                <td className="px-4 py-4 text-stone-600">
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="w-4 h-4 text-stone-400" />
                    {row.peers}
                  </span>
                </td>

                <td className="px-4 py-4 text-stone-600">
                  <span className="inline-flex items-center gap-1.5">
                    <Radio className="w-4 h-4 text-stone-400" />
                    {row.trackers}
                  </span>
                </td>

                <td className="px-4 py-4 text-right font-medium text-stone-800">
                  <span className="inline-flex items-center gap-1.5">
                    <Gauge className="w-4 h-4 text-green-500" />
                    {row.speed}
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