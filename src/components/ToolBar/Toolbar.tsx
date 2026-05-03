import {
  Plus,
  Link,
  Play,
  Pause,
  Square,
  Trash2,
  Search,
} from "lucide-react";
import { useState } from "react";

const Toolbar = () => {
  const [active, setActive] = useState<string | null>(null);

  return (
    <div className="sticky top-0 z-50 w-full h-16 bg-blue-100 border-b border-blue-200 px-4 py-2 flex items-center gap-2">

      <ToolbarButton
        icon={<Plus size={16} />}
        label="Add"
        active={active === "add"}
        onClick={() => setActive("add")}
      />

      <ToolbarButton
        icon={<Link size={16} />}
        label="Magnet"
        active={active === "magnet"}
        onClick={() => setActive("magnet")}
      />

      <Divider />

      <ToolbarButton
        icon={<Play size={16} />}
        label="Start"
        active={active === "start"}
        onClick={() => setActive("start")}
      />

      <ToolbarButton
        icon={<Pause size={16} />}
        label="Pause"
        active={active === "pause"}
        onClick={() => setActive("pause")}
      />

      <ToolbarButton
        icon={<Square size={16} />}
        label="Stop"
        active={active === "stop"}
        onClick={() => setActive("stop")}
      />

      <Divider />

      <ToolbarButton
        icon={<Trash2 size={16} />}
        label="Remove"
        active={active === "remove"}
        onClick={() => setActive("remove")}
        danger
      />

      {/* Search */}
      <div className="ml-auto flex items-center bg-white border border-blue-200 rounded-md px-3 h-9 w-64">
        <Search className="w-4 h-4 text-stone-400 mr-2" />
        <input
          type="text"
          placeholder="Search..."
          className="w-full text-sm bg-transparent outline-none"
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
            ? "bg-white text-blue-700 rounded font-medium"
            : danger
            ? "text-red-600 hover:bg-red-50"
            : "text-stone-800 hover:bg-blue-50"
        }`}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
};

const Divider = () => (
  <div className="w-px h-6 bg-blue-300 mx-1" />
);