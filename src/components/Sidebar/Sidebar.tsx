import React from "react";
import {
  ArrowUpDown,
  Wifi,
  MonitorSmartphone,
  ArrowLeft,
  ArrowRight,
  Home,
  Settings,
  User,
} from "lucide-react";

type SidebarProps = {
  setPage: React.Dispatch<React.SetStateAction<string>>;
  isSidebarOpen: boolean;
  page: string;
  setIsSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

const menuItems = [
  { id: "home", label: "Home", icon: Home },
  { id: "torrent", label: "Torrent", icon: ArrowUpDown },
  { id: "network", label: "Feeds", icon: Wifi },
  { id: "devices", label: "Devices", icon: MonitorSmartphone },
  { id: "settings", label: "Settings", icon: Settings },
];

export const Sidebar = ({
  setPage,
  page,
  isSidebarOpen,
  setIsSidebarOpen,
}: SidebarProps) => {
  return (
    <div
      className={`h-screen flex flex-col bg-blue-100 border-r border-blue-200 transition-all duration-300 ${
        isSidebarOpen ? "w-80" : "w-20"
      }`}
    >
      {/* Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-blue-200">
        {isSidebarOpen && (
          <span className="font-bold text-lg whitespace-nowrap text-stone-900">
            Torrent Client
          </span>
        )}

        <button
          type="button"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-full hover:bg-white transition ml-auto"
        >
          {isSidebarOpen ? (
            <ArrowLeft className="w-6 h-6" />
          ) : (
            <ArrowRight className="w-6 h-6" />
          )}
        </button>
      </div>

      {/* Menu */}
      <nav className="flex flex-col w-full py-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const active = page === item.id;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setPage(item.id)}
              className={`w-full flex items-center gap-4 px-5 py-4 text-left transition-all ${
                active
                  ? "bg-white text-blue-700 font-medium border-l-4 border-blue-500"
                  : "text-stone-800 hover:bg-blue-50 border-l-4 border-transparent"
              }`}
            >
              <Icon className="w-6 h-6 shrink-0" />

              {isSidebarOpen && (
                <span className="text-xl whitespace-nowrap">
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom user/status section */}
      <div className="mt-auto p-3 border-t border-blue-200">
        <div
          className={`flex items-center gap-3 rounded-lg w-[78%] bg-white px-3 py-3 shadow-sm ${
            !isSidebarOpen ? "justify-center" : ""
          }`}
        >
          <div className="h-9 w-9 rounded-full bg-blue-500 text-white flex items-center justify-center">
            <User className="w-5 h-5" />
          </div>

          {isSidebarOpen && (
            <div>
              <p className="text-sm font-semibold text-stone-800">Dan</p>
              <p className="text-xs text-green-600">Online</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};