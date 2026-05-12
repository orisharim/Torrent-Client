import React from "react";
import {
  ArrowUpDown,
  Wifi,
  MonitorSmartphone,
  Home,
  Settings,
} from "lucide-react";

type TabsProps = {
  setPage: React.Dispatch<React.SetStateAction<string>>;
  page: string;
};

const tabItems = [
  { id: "home", label: "Home", icon: Home },
  { id: "torrent", label: "Torrent", icon: ArrowUpDown },
  { id: "network", label: "Network", icon: Wifi },
  { id: "devices", label: "Devices", icon: MonitorSmartphone },
  { id: "settings", label: "Settings", icon: Settings },
];

const Tabs: React.FC<TabsProps> = ({ setPage, page }) => {
  return (
    <div className="flex items-center bg-blue-100 dark:bg-blue-950 rounded-full px-2 py-2 gap-1 shadow-inner border border-blue-200 dark:border-blue-800 w-fit mx-4 mt-4">
      {tabItems.map((item) => {
        const IconComponent = item.icon;
        const active = page === item.id;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => setPage(item.id)}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-full
              transition-all duration-200 text-sm font-medium
              ${
                active
                  ? "bg-blue-600 text-white shadow-md"
                  : "text-blue-500 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800 hover:text-blue-700 dark:hover:text-blue-200"
              }
            `}
          >
            <IconComponent size={16} />
            {item.label}
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;
