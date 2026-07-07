import {
  ArrowUpDown,
  Wifi,
  MonitorSmartphone,
  Home,
  Settings,
} from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";
import { useUI } from "../../context/UIContext";
import type { Page } from "../../context/UIContext";

const Tabs = () => {
  const { t } = useLanguage();
  const { page, setPage } = useUI();

  const tabItems: { id: Page; label: string; icon: typeof Home }[] = [
    { id: "home", label: t("nav.home"), icon: Home },
    { id: "torrent", label: t("nav.torrent"), icon: ArrowUpDown },
    { id: "network", label: t("nav.network"), icon: Wifi },
    { id: "devices", label: t("nav.devices"), icon: MonitorSmartphone },
    { id: "settings", label: t("nav.settings"), icon: Settings },
  ];

  return (
    <div className="flex items-center bg-blue-100 dark:bg-blue-950 rounded-full px-2 py-2 gap-1 shadow-inner border border-blue-200 dark:border-blue-800 w-fit max-w-[calc(100%-2rem)] overflow-x-auto mx-4 mt-4">
      {tabItems.map((item) => {
        const IconComponent = item.icon;
        const active = page === item.id;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => setPage(item.id)}
            title={item.label}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-full shrink-0
              transition-all duration-200 text-sm font-medium
              ${
                active
                  ? "bg-blue-600 text-white shadow-md"
                  : "text-blue-500 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800 hover:text-blue-700 dark:hover:text-blue-200"
              }
            `}
          >
            <IconComponent size={16} />
            <span className="hidden sm:inline">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;
