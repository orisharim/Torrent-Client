import asyncio
import torrents_manager

     
async def main():
    torrent_file_path = "/home/ori/Desktop/dunkirk.torrent"
    download_path = "/home/ori/Desktop/dunkirk"
    try:
        await torrents_manager.start_torrent_client()

        res = await torrents_manager.add_torrent(torrent_file_path, download_path)
        if res:
            print("Torrent added successfully.")
            while True:
                await asyncio.sleep(5)

        else:
            print("Failed to add torrent.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await torrents_manager.stop_torrent_client()
asyncio.run(main())