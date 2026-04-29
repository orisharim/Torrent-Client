import {Plus , Link} from 'lucide-react'


export const HomePage = () => {
  return (
    <div className="p-4 flex flex-col gap-4">
      {/* header */}
      <span className='h-4 font-bold text-2xl mb-4 text-center'>Home</span>
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-stone-100 p-4 rounded shadow">Download: 
          const downloading = 
        </div>
        <div className="bg-stone-100 p-4 rounded shadow">Upload: 0.3 MB/s</div>
        <div className="bg-stone-100 p-4 rounded shadow">Active: 3</div>
        <div className="bg-stone-100 p-4 rounded shadow">Seeding: 2</div>
      </div>

      {/* Quick actions */}
      <div className='h-14 sticky top-0 z-10 flex items-center gap-1 px-2 bg-stone-100 font-bold shadow'>
        <button className='flex items-center gap-2 px-3 py-2 rounded hover:border-2'>
          <Plus size={18}/>
          <span className="hidden sm:inline">Add Torrent</span>
        </button>

        <button className='flex items-center gap-2 px-3 py-2 rounded hover:border-2'>
          <Link size={18}/>
          <span className="hidden sm:inline">Magnet</span>
        </button>
      </div>
      

      {/* Recent */}
      <div className="bg-stone-100 p-4 rounded shadow">
        <h2 className="font-bold mb-2">Recent Torrents</h2>
        <div>ubuntu.iso - Completed</div>
        <div>movie.mp4 - Paused</div>
      </div>

    </div>
  );
};