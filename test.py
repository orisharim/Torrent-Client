from asyncio import timeouts
from peers.peer_connection import PeerConnection
from piece_manager import PieceManager
from torrent_file import TorrentFile
from torrent_storage import TorrentStorage
import tracker
import os
import asyncio

async def print_progress():
    downloaded_pieces_count = len(await manager._torrent_storage.get_downloaded_pieces())
    print(f"Downloaded pieces: {downloaded_pieces_count}/{manager._torrent_storage._total_piece_count}")

     
async def main():
    global manager, time
    time = 0

    torrent = TorrentFile("/home/ori/Desktop/dunkirk.torrent")


    _, peers = await tracker.get_peers(torrent, peer_id=b'-PC0001-123456789012')

    # peer_info = peers[1] if peers else None

    # print("peer info:", peer_info)
    # peer_connection = PeerConnection(peer_info[0], peer_info[1], torrent.info_hash, b'-PC0001-123456789012', TorrentStorage(torrent, "./downloads"))

    # await peer_connection.connect()
    
    # while not await peer_connection.is_connected():
    #     await asyncio.sleep(0.1)

    # await peer_connection.start_message_loop()

    # while not await peer_connection.is_message_loop_running():
    #     await asyncio.sleep(0.1)

    # print("Connected to peer and message loop started.")

    # await asyncio.sleep(15)  # Wait for some time to receive messages

    # print("Closing peer connection.")
    # await peer_connection.disconnect()     


    # Create a PieceManager instance
    manager = PieceManager(peer_id=b'-PC0001-123456789012', peers_info=peers, torrent_metadata=torrent, download_path="/home/ori/Desktop")

    # Start the download process
    await manager.start_downloads()
    await manager.start_seeding()

    # Wait for the download to complete
    while not await manager.is_complete():
        await asyncio.sleep(10)
        await print_progress()
    
    print("Download complete!")
    print(f"Total time taken: {time} seconds")
    print(f"Downloaded pieces: {len(await manager._torrent_storage.get_downloaded_pieces())}/{manager._torrent_storage._total_piece_count}")
    await manager.close_all()

asyncio.run(main())