import asyncio
import torrents_manager

     
async def main():

    torrent_settings = torrents_manager.TorrentSettings()

    torrent_file_path = "/home/ori/Desktop/torrentsfortest/ubuntu-26.04.1-desktop-amd64.iso.torrent"
    download_path = "/home/ori/Desktop/ubuntu"
    try:
        await torrents_manager.start_torrent_client()
        res = await torrents_manager.add_new_torrent(torrent_file_path, download_path, torrent_settings)
        print("@@@@@@@@@@@@@@@@!!!!!!!!!!!!!BALLS!!!!!!!!!!!!")
        if res:
            state = await torrents_manager.get_torrent_state(torrent_file_path)
            print(f"{len(await state.storage.get_downloaded_pieces())} : {state.storage.get_total_piece_count()}")
            while True:
                print(f"{len(await state.storage.get_downloaded_pieces())} : {state.storage.get_total_piece_count()}")
                await asyncio.sleep(5)

        else:
            print("Failed to add torrent.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await torrents_manager.stop_torrent_client()
asyncio.run(main())