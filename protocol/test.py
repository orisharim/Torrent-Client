from peer_connection import PeerConnection
from piece_manager import PieceManager
from torrent import Torrent
from torrent_storage import TorrentStorage
import tracker
import os
import asyncio

async def print_progress():
    global time
    while True:
        await asyncio.sleep(1)
        time += 1
        downloaded_pieces = await manager._torrent_storage.get_downloaded_pieces()
        print(f"Time: {time}s, Downloaded pieces: {len(downloaded_pieces)}/{manager._torrent_storage._total_piece_count}")

     
async def main():
    global manager, time
    time = 0

    torrent_file_path = "./ubuntu.torrent"
    torrent = Torrent(torrent_file_path)

    peers = tracker.get_peers(torrent, peer_id=b'-PC0001-123456789012', port=6881)

    peer_info = peers[2] if peers else None

    print("peer info:", peer_info)
    peer_connection = PeerConnection(peer_info[0], peer_info[1], torrent.info_hash, b'-PC0001-123456789012', TorrentStorage(torrent, "./downloads"))

    await peer_connection.connect()
    
    while not await peer_connection.is_connected():
        await asyncio.sleep(0.1)

    await peer_connection.start_message_loop()

    while not await peer_connection.is_message_loop_running():
        await asyncio.sleep(0.1)

    print("Connected to peer and message loop started.")

    await asyncio.sleep(15)  # Wait for some time to receive messages

    print("Closing peer connection.")
    await peer_connection.disconnect()     


    # Create a PieceManager instance
    # manager = PieceManager(peer_id=b'-PC0001-123456789012', peers_info=peers, torrent_metadata=torrent, download_path="downloads")

    # # Start the download process
    # await manager.start_downloads()

    # # Start the progress printing task
    # progress_task = asyncio.create_task(print_progress())

    # # Wait for the download to complete
    # while not await manager.is_complete():
    #     await asyncio.sleep(1)

    # # Cancel the progress printing task
    # progress_task.cancel()

    # print("Download complete!")
    # print(f"Total time taken: {time} seconds")
    # print(f"Downloaded pieces: {len(await manager._torrent_storage.get_downloaded_pieces())}/{manager._torrent_storage._total_piece_count}")

asyncio.run(main())