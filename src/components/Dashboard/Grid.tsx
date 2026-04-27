import React from "react";
import { TorrentTable } from "./TorrenTable";

export const Grid = () => {
  return (
    <div className="px-4 grid gap-3 mt-3 grid-cols-12">
      <div className="col-span-12">
        <TorrentTable />
      </div>
    </div>
  );
};