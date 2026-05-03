import React from "react";
import { Plus, RefreshCw, Download, Rss } from "lucide-react";

const feeds = [
  {
    id: 1,
    source: "Ubuntu Releases",
    name: "ubuntu-24.04.iso",
    size: "2.5 GB",
    date: "Today",
  },
  {
    id: 2,
    source: "Movie Feed",
    name: "movie.2026.1080p.mkv",
    size: "1.4 GB",
    date: "Yesterday",
  },
  {
    id: 3,
    source: "Linux Tools",
    name: "linux_tools.tar.gz",
    size: "4.7 GB",
    date: "2 days ago",
  },
];

export const FeedsPage = () => {
  return (
    <div className="w-full min-h-screen bg-stone-50 p-6 flex flex-col gap-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Feeds</h1>
          <p className="text-sm text-stone-500 mt-1">
            Manage RSS feeds and download torrents automatically
          </p>
        </div>

        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm shadow-sm transition">
            <Plus size={16} />
            Add Feed
          </button>

          <button className="flex items-center gap-2 px-3 py-2 border border-blue-200 hover:bg-blue-50 text-stone-600 rounded-md text-sm transition">
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats (optional but pro) */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-stone-500">Total Feeds</p>
          <p className="text-xl font-bold">{feeds.length}</p>
        </div>

        <div className="bg-white border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-stone-500">New Today</p>
          <p className="text-xl font-bold text-blue-600">1</p>
        </div>

        <div className="bg-white border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-stone-500">Downloads Ready</p>
          <p className="text-xl font-bold text-green-600">3</p>
        </div>
      </div>

      {/* Table */}
      <div className="w-full border border-blue-200 rounded-xl overflow-hidden shadow-sm bg-white">

        {/* Table header bar */}
        <div className="px-4 py-3 border-b border-blue-100 bg-blue-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-blue-800 flex items-center gap-2">
            <Rss className="w-4 h-4" />
            Feed Items
          </h2>

          <span className="text-xs text-stone-500">
            {feeds.length} items
          </span>
        </div>

        <table className="w-full text-sm">

          <thead className="bg-white border-b border-blue-100">
            <tr className="text-left text-stone-500">
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Torrent</th>
              <th className="px-4 py-3 font-medium">Size</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>

          <tbody>
            {feeds.map((feed, index) => (
              <tr
                key={feed.id}
                className={`border-b border-blue-50 last:border-b-0 transition
                  ${index % 2 === 1 ? "bg-blue-50/40" : "bg-white"}
                  hover:bg-blue-50`}
              >
                <td className="px-4 py-4 text-stone-700">
                  {feed.source}
                </td>

                <td className="px-4 py-4">
                  <div className="font-medium text-stone-800">
                    {feed.name}
                  </div>
                  <div className="text-xs text-stone-400">
                    ID #{feed.id}
                  </div>
                </td>

                <td className="px-4 py-4 text-stone-600">
                  {feed.size}
                </td>

                <td className="px-4 py-4 text-stone-600">
                  {feed.date}
                </td>

                <td className="px-4 py-4 text-right">
                  <button className="inline-flex items-center gap-2 rounded-md border border-blue-200 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 transition">
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </td>
              </tr>
            ))}
          </tbody>

        </table>
      </div>
    </div>
  );
};