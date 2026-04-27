import { Plus, Link, Play, Pause, Square, Trash2, Search } from "lucide-react";

const Toolbar = () => {
  return (
    <div className="h-14 sticky top-0 z-10 flex items-center gap-1 px-2 bg-stone-300">
      <button className="flex items-center gap-2 px-3 py-2 rounded hover:bg-stone-50">
        <Plus size={18} />
        <span className="hidden sm:inline">Add</span>
      </button>

      <button className="flex items-center gap-2 px-3 py-2 rounded hover:bg-stone-50">
        <Link size={18} />
        <span className="hidden sm:inline">Magnet</span>
      </button>

      <div className="w-px h-6 bg-stone-400 mx-1" />

      <button className="flex items-center gap-2 px-3 py-2 rounded hover:bg-stone-50">
        <Play size={18} />
        <span className="hidden sm:inline">Start</span>
      </button>

      <button className="flex items-center gap-2 px-3 py-2 rounded hover:bg-stone-50">
        <Pause size={18} />
        <span className="hidden sm:inline">Pause</span>
      </button>

      <button className="flex items-center gap-2 px-3 py-2 rounded hover:bg-stone-50">
        <Square size={18} />
        <span className="hidden sm:inline">Stop</span>
      </button>

      <div className="w-px h-6 bg-stone-400 mx-1" />

      <button className="flex items-center gap-2 px-3 py-2 rounded hover:bg-stone-50">
        <Trash2 size={18} />
        <span className="hidden sm:inline">Remove</span>
      </button>

      <div className="ml-auto flex items-center bg-white border border-stone-300 rounded px-2">
        <Search size={18} />
        <input
          type="text"
          placeholder="Search..."
          className="h-8 px-2 text-sm outline-none bg-transparent"
        />
      </div>
    </div>
  );
};

export default Toolbar;