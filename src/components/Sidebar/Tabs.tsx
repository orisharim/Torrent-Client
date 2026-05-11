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
  { id: "network", label: "Feeds", icon: Wifi },
  { id: "devices", label: "Devices", icon: MonitorSmartphone },
  { id: "settings", label: "Settings", icon: Settings },
];

const Tabs: React.FC<TabsProps> = ({ setPage, page }) => {
  return (
    <div className="m-4 bg-blue-100 rounded-lg p-2 flex gap-2 flex-wrap">
      {tabItems.map((item) => {
        const IconComponent = item.icon;
        const active = page === item.id;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => setPage(item.id)}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg
              transition-all duration-200 font-medium
              ${
                active
                  ? "bg-blue-600 text-white shadow-lg"
                  : "bg-blue-100 text-black hover:bg-stone-50 hover:text-blue-600"
              }
            `}
          >
            <IconComponent size={20} />
            {item.label}
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;