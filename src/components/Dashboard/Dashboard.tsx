import React from "react";
import { Grid } from "./Grid";
import Toolbar from "../ToolBar/Toolbar";
import { HomePage } from "../Views/HomePage";
import {TorrentPage} from "../Views/TorrentPage";

type DashboardProps = {
  page: string;
};

export const Dashboard = ({ page }: DashboardProps) => {
  return (
    
    <div className="bg-stone-50 sticky top-0 h-[200vh] w-full">

        <Toolbar/>
        <Grid/>
      {page === "home" && <HomePage/>}

      {page === "torrent" && <TorrentPage/>}

      {page === "network" && <div>Network Page</div>}

      {page === "devices" && <div>Devices Page</div>}

    </div>


  );
};

