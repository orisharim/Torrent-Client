from piece_manager import PieceManager
from torrent import Torrent
from torrent_storage import TorrentStorage
import tracker
import os
import asyncio

torrent = Torrent('./protocol//ubuntu.torrent')

print(torrent.summary())

torrent_storage = TorrentStorage(torrent.piece_length, len(torrent.pieces), torrent.files_info, "./downloaded")
peer_id = os.urandom(20)
peers = tracker.get_peers(torrent, peer_id)
piece_manager = PieceManager(peer_id, peers, torrent, "./downloaded")

async def main():
    await piece_manager.connect_to_all_peers()
    print("connected to all peers")      
    await piece_manager.start_downloads()
    
    # monitor the download progress
    try:
        while not piece_manager.is_complete():
            downloaded = piece_manager.get_downloaded_piece_count()
            total = piece_manager._total_piece_count
            percent = (downloaded / total) * 100 if total > 0 else 0
            print(f"Download Progress: {downloaded}/{total} pieces ({percent:.2f}%)")
            print(f"Bitfield: {piece_manager._bitfield}")
            await asyncio.sleep(5)
        print("Download complete!")
    except KeyboardInterrupt:
        print("Stopping download...")
    finally:
        await piece_manager.close_all()

    success = await piece_manager._validate_all_pieces()
    while not success:
        try:
            while not piece_manager.is_complete():
                downloaded = piece_manager.get_downloaded_piece_count()
                total = piece_manager._total_piece_count
                percent = (downloaded / total) * 100 if total > 0 else 0
                print(f"Download Progress: {downloaded}/{total} pieces ({percent:.2f}%)")
                print(f"Bitfield: {piece_manager._bitfield}")
                await asyncio.sleep(5)
                print("Download complete!")
        except KeyboardInterrupt:
            print("Stopping download...")
        finally:
            await piece_manager.close_all()
        success = await piece_manager._validate_all_pieces()

        
        

asyncio.run(main())
