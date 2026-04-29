import React from "react";

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
    <div className="p-4 items-center w-full">

      {/* header */}
      <div className="text-center">
        <span className='h-4 font-bold text-2xl mb-4 mt-4'>Torrents</span>
      </div>
      {/* Stats */}
      <table className="m-4 w-full bg-stone-50 rounded-md overflow-hidden shadow">
        <TableHead />
        <TableBody />
      </table>
    </div>
  );
};

const TableHead = () => {
  return (
    <thead>
      <tr className="text-sm border-b border-stone-300 text-left bg-stone-100">
        <th className="p-2">Files</th>
        <th className="p-2">Info</th>
        <th className="p-2">Peers</th>
        <th className="p-2">Trackers</th>
        <th className="p-2">Speed</th>
      </tr>
    </thead>
  );
};

const TableBody = () => {
  return (
    <tbody>
      {tableData.map((row) => (
        <tr
          key={row.id}
         className={`text-sm ${row.id % 2 ? "bg-stone-300" : ""}`}
        >
          <td className="p-2">{row.files}</td>
          <td className="p-2">{row.info}</td>
          <td className="p-2">{row.peers}</td>
          <td className="p-2">{row.trackers}</td>
          <td className="p-2">{row.speed}</td>
        </tr>
      ))}
    </tbody>
  );
};