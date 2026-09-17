import { ArrowUpDown, Home, Settings } from "lucide-react";
import { useUI } from "../../context/UIContext";
import type { Page } from "../../context/UIContext";

const Sidebar = () => {
  const { page, setPage } = useUI();

  const navItems: { id: Page; label: string; icon: typeof Home }[] = [
    { id: "home", label: "Home", icon: Home },
    { id: "torrent", label: "Torrent", icon: ArrowUpDown },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 flex flex-col bg-white dark:bg-stone-900 border-e border-blue-100 dark:border-blue-900 px-3 py-5">
      <div className="px-2 mb-6 text-lg font-bold text-stone-800 dark:text-stone-100">
        Torrent Client
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map((item) => {
          const IconComponent = item.icon;
          const active = page === item.id;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setPage(item.id)}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg
                text-sm font-medium transition-colors border-s-4
                ${
                  active
                    ? "border-blue-600 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-stone-600 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800"
                }
              `}
            >
              <IconComponent size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
};

export default Sidebar;
