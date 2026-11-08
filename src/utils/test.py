import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torrents_manager


async def main():

    torrent_settings = torrents_manager.TorrentSettings()

    torrent_file_path = "/home/ori/Desktop/torrentsfortest/ubun.torrent"
    download_path = "/home/ori/Desktop/torrentsfortest/ubuntu"
    info_hash = torrents_manager.TorrentFile(torrent_file_path).info_hash
    try:
        await torrents_manager.start_torrent_client()
        res = await torrents_manager.add_new_torrent(torrent_file_path, "/home/ori/Desktop/torrentsfortest/ubuntu1", torrent_settings)
        await torrents_manager.change_torrent_status(info_hash, "/home/ori/Desktop/torrentsfortest/ubuntu1", is_downloading=True, is_seeding=True)

       
        while True:
            await asyncio.sleep(5)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await torrents_manager.stop_torrent_client()
asyncio.run(main())