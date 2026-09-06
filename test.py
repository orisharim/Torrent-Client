from asyncio import timeouts
from peers.peer_connection import PeerConnection
from piece_manager import PieceManager
from port_forward import forward_port
from port_forward import delete_port
from torrent_file import TorrentFile
from torrent_storage import TorrentStorage
import tracker
import os
import asyncio
import upnpy

async def print_progress():
    downloaded_pieces_count = len(await manager._torrent_storage.get_downloaded_pieces())
    print(f"Downloaded pieces: {downloaded_pieces_count}/{manager._torrent_storage._total_piece_count}")

     
async def main():
    global manager, time
    time = 0


    service = await forward_port(6881, protocol="TCP", description="Torrent Client")
    await delete_port(service, 6881, protocol="TCP")    
    # torrent = TorrentFile("/home/ori/Desktop/dunkirk.torrent")

    # _, peers = await tracker.get_peers(torrent, peer_id=b'-PC0001-123456789012')

        
    # manager = PieceManager(peer_id=b'-PC0001-123456789012', peers_info=peers, torrent_metadata=torrent, download_path="/home/ori/Desktop")

    # await manager.start_downloads()
    # await manager.start_seeding()

    # while not await manager.is_complete():
    #     await asyncio.sleep(10)
    #     await print_progress()
    
    # print("Download complete!")
    # print(f"Total time taken: {time} seconds")
    # print(f"Downloaded pieces: {len(await manager._torrent_storage.get_downloaded_pieces())}/{manager._torrent_storage._total_piece_count}")
    # await manager.close_all()

asyncio.run(main())