import asyncio
import torrents_manager

     
async def main():

    torrent_settings = torrents_manager.TorrentSettings()

    torrent_file_path = "/home/ori/Desktop/torrentsfortest/ubuntu-26.04.1-desktop-amd64.iso.torrent"
    download_path = "/home/ori/Desktop/ubuntu"
    try:
        await torrents_manager.start_torrent_client()
        res = await torrents_manager.add_new_torrent(torrent_file_path, download_path, torrent_settings)
        await torrents_manager.change_torrent_status(torrent_file_path, is_downloading=False, is_seeding=True)
        print("@@@@@@@@@@@@@@@@!!!!!!!!!!!!!!!!")

        if res:
            while True:
                print("status: ", await torrents_manager.get_torrent_status(torrent_file_path))
                await asyncio.sleep(5)

        else:
            print("Failed to add torrent.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await torrents_manager.stop_torrent_client()
asyncio.run(main())