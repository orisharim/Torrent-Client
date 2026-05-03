import React from "react";
import {
  ArrowUpDown,
  Wifi,
  MonitorSmartphone,
  ArrowLeft,
  ArrowRight,
  Home,
} from "lucide-react";

type SidebarProps = {
  setPage: React.Dispatch<React.SetStateAction<string>>;
  isSidebarOpen: boolean;
  page: string;
  setIsSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

export const Sidebar = ({
  setPage,
  page,
  isSidebarOpen,
  setIsSidebarOpen,
}: SidebarProps) => {
  const menuItem = (active: boolean) =>
    `w-full flex items-center gap-3 px-4 py-3 hover:bg-stone-50 transition-colors ${
      active ? "bg-stone-50" : "bg-blue-100"
    }`;

  return (
    <div className="h-screen flex flex-col bg-blue-100">
      {/* Header */}
      <div className="h-16 px-4 flex items-center justify-between">
        {isSidebarOpen && (
          <span className="font-bold text-lg whitespace-nowrap">
            Torrent Client ndf
          </span>
        )}

        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-full hover:bg-stone-50 "
        >
          {isSidebarOpen ? (
            <ArrowLeft className="w-6 h-6" />
          ) : (
            <ArrowRight className="w-6 h-6" />
          )}
        </button>
      </div>

      {/* Menu */}
      <div className="flex flex-col w-full -mt-2">
        <button onClick={() => setPage("home")} className={menuItem(page === "home")}>
          <Home className="w-6 hover:bg-stone-700 h-6 marker: shrink-0" />
          {isSidebarOpen && <span className="text-xl">Home</span>}
        </button>

        <button onClick={() => setPage("torrent")} className={menuItem(page === "torrent")}>
          <ArrowUpDown className="w-6 h-6 shrink-0" />
          {isSidebarOpen && <span className="text-xl">Torrent</span>}
        </button>

        <button onClick={() => setPage("network")} className={menuItem(page === "network")}>
          <Wifi className="w-6 h-6 shrink-0" />
          {isSidebarOpen && <span className="text-xl">Feeds</span>}
        </button>

        <button onClick={() => setPage("devices")} className={menuItem(page === "devices")}>
          <MonitorSmartphone className="w-6 h-6 shrink-0" />
          {isSidebarOpen && <span className="text-xl">Devices</span>}
        </button>
      </div>
    </div>
  );
};