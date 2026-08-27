from asyncio import timeouts
from peer_connection import PeerConnection
from piece_manager import PieceManager
from torrent import Torrent
from torrent_storage import TorrentStorage
import tracker
import os
import asyncio

     
async def main():
    global manager, time
    time = 0

    torrent_file_path = "./ubuntu.torrent"
    torrent = Torrent(torrent_file_path)

    try:
        peers = tracker.get_peers(torrent, peer_id=b'-PC0001-123456789012', port=6881)
    except Exception as e:
        print(f"Tracker request failed ({e}). Using cached/fallback peer list...")
        peers = [
            ("185.125.190.59", 6905),
            ("185.125.190.59", 6942),
            ("2a01:e11:100e:cb60:4dfd:eb2f:e88f:bf7f", 51413),
            ("2001:41d0:303:9b68::2", 17005),
            ("2a01:e0a:ac9:fc01::2", 51413),
            ("2a03:3b40:2c:1::3", 64666),
            ("2607:fea8:fdf0:825b:74e1:7d39:3f9e", 51413),
            ("2400:4050:a560:9c00:caa3:62ff:fec5:1a90", 1484)
        ]

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
    manager = PieceManager(peer_id=b'-PC0001-123456789012', peers_info=peers, torrent_metadata=torrent, download_path="~/Desktop")

    # Start the download process
    await manager.start_downloads()

    # Wait for the download to complete
    while not await manager.is_complete():
        await asyncio.sleep(1)
    
    print("Download complete!")
    print(f"Total time taken: {time} seconds")
    print(f"Downloaded pieces: {len(await manager._torrent_storage.get_downloaded_pieces())}/{manager._torrent_storage._total_piece_count}")

asyncio.run(main())