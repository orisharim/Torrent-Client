import asyncio
import torrents_manager

     
async def main():

    torrent_settings = torrents_manager.TorrentSettings()

    torrent_file_path = "/home/ori/Desktop/torrentsfortest/ubuntu-26.04.1-desktop-amd64.iso.torrent"
    download_path = "/home/ori/Desktop/torrentsfortest/ubuntu1"
    info_hash = torrents_manager.TorrentFile(torrent_file_path).info_hash
    try:
        await torrents_manager.start_torrent_client()
        res = await torrents_manager.add_new_torrent(torrent_file_path, "/home/ori/Desktop/torrentsfortest/ubuntu1", torrent_settings)
        res = await torrents_manager.add_new_torrent(torrent_file_path, "/home/ori/Desktop/torrentsfortest/ubuntu2", torrent_settings)
        print("@@@@@@@@@@@@@@@@!!!!!!!!!!!!!!!!")
        await torrents_manager.change_torrent_status(info_hash, "/home/ori/Desktop/torrentsfortest/ubuntu1", is_downloading=True, is_seeding=True)
        print("@@@@@@@@@@@@@@@@!!!!!!!!!!!!!!!!")
        await torrents_manager.change_torrent_status(info_hash, "/home/ori/Desktop/torrentsfortest/ubuntu2", is_downloading=True, is_seeding=True)
        print("@@@@@@@@@@@@@@@@!!!!!!!!!!!!!!!!")

        if res:
            while True:
                await asyncio.sleep(5)

        else:
            print("Failed to add torrent.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await torrents_manager.stop_torrent_client()
asyncio.run(main())