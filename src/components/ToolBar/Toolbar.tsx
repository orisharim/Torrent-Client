import {
  Plus,
  Link,
  Square,
  Trash2,
  Search,
} from "lucide-react";
import { useState } from "react";

const Toolbar = () => {
  const [active, setActive] = useState<string | null>(null);

  return (
    <div className="sticky top-0 z-50 w-full h-16 bg-blue-100 dark:bg-stone-900 border-b border-blue-200 dark:border-blue-900 px-4 py-2 flex items-center gap-2">

      <button
        onClick={() => setActive("add")}
        className={`flex font-bold items-center gap-2 px-3 py-2 text-sm transition
          ${active === "add"
            ? "bg-blue-600 text-white font-bold rounded"
            : "text-stone-800 dark:text-stone-200 hover:bg-blue-200 dark:hover:bg-blue-900 hover:font-bold"
          }
        `}
      >
        <Plus size={20} className="font-bold" />
        <span className="hidden sm:inline">Add Torrent</span>
      </button>

      <ToolbarButton
        icon={<Link size={16} />}
        label="Magnet"
        active={active === "magnet"}
        onClick={() => setActive("magnet")}
      />

      <Divider />

      <ToolbarButton
        icon={<Square size={16} />}
        label="Stop"
        active={active === "stop"}
        onClick={() => setActive("stop")}
      />

      <ToolbarButton
        icon={<Trash2 size={16} />}
        label="Remove"
        active={active === "remove"}
        onClick={() => setActive("remove")}
        danger
      />

      <div className="ml-auto flex items-center bg-white dark:bg-stone-800 border border-blue-200 dark:border-blue-800 rounded-md px-3 h-9 w-64">
        <Search className="w-4 h-4 text-stone-400 dark:text-stone-500 mr-2" />
        <input
          type="text"
          placeholder="Search..."
          className="w-full text-sm bg-transparent outline-none text-stone-800 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-500"
        />
      </div>
    </div>
  );
};

export default Toolbar;

const ToolbarButton = ({
  icon,
  label,
  active,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  danger?: boolean;
}) => {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 text-sm transition
        ${
          active
            ? "bg-white dark:bg-stone-700 text-blue-700 dark:text-blue-300 rounded font-medium"
            : danger
            ? "text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
            : "text-stone-800 dark:text-stone-200 hover:bg-blue-200 dark:hover:bg-blue-900"
        }`}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
};

const Divider = () => (
  <div className="w-px h-6 bg-blue-300 dark:bg-blue-700 mx-1" />
);
