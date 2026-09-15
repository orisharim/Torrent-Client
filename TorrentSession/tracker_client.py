import socket
import struct
import random
import urllib.parse
import urllib.request
import asyncio
from typing import List, Tuple, Dict, Any, Optional
from Torrent.bencode import decode_bencode
from TorrentSession.peers.peers import Peers
from TorrentSession.torrent_storage import TorrentStorage
from TorrentSession.contact_tracker import contact_tracker, parse_tracker_response
import TorrentSession.contact_tracker as tracker_protocol

class TrackerClient:

    DEFAULT_CONTACT_INTERVAL = 10.0

    def __init__(self, peers : Peers, tracker_url: str, info_hash: bytes, peer_id: bytes, listening_port: int, torrent_storage: TorrentStorage) -> None:
        self._peers = peers
        self._tracker_url = tracker_url
        self._info_hash = info_hash
        self._peer_id = peer_id
        self._listening_port = listening_port
        self._torrent_storage = torrent_storage
        self._recontact_task = None

    async def contact(self) -> bool:
        downloaded_pieces = await self._torrent_storage.get_downloaded_pieces()
        resp = await contact_tracker(
            tracker_url=self._tracker_url,
            info_hash=self._info_hash,
            peer_id=self._peer_id,
            listening_port=self._listening_port,
            event=tracker_protocol.STARTED,
            downloaded=sum(self._torrent_storage.get_piece_length(index) for index in downloaded_pieces),
            uploaded=await self._torrent_storage.get_uploaded_bytes(),
            left=self._torrent_storage._torrent_metadata.length - sum(
                self._torrent_storage.get_piece_length(index) for index in downloaded_pieces
            ),
        )

        interval, peers = parse_tracker_response(resp)
        if not peers:
            return False

        if interval is None:
            interval = self.DEFAULT_CONTACT_INTERVAL

        await self._peers.add_peers(peers)

        self._recontact_task = asyncio.create_task(self._recontact(interval))
        return True

    async def _recontact(self, interval: float):
        while True:
            await asyncio.sleep(interval)
            try:
                downloaded_pieces = await self._torrent_storage.get_downloaded_pieces()
                downloaded_bytes = sum(
                    self._torrent_storage.get_piece_length(index)
                    for index in downloaded_pieces
                )
                resp = await contact_tracker(
                    tracker_url=self._tracker_url,
                    info_hash=self._info_hash,
                    peer_id=self._peer_id,
                    listening_port=self._listening_port,
                    event=tracker_protocol.KEEP_ALIVE,
                    downloaded=downloaded_bytes,
                    uploaded=await self._torrent_storage.get_uploaded_bytes(),
                    left=self._torrent_storage._torrent_metadata.length - downloaded_bytes,
                )

                next_interval, peers = parse_tracker_response(resp)
                if peers:
                    await self._peers.add_peers(peers)
                if next_interval is not None:
                    interval = max(next_interval, 1)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"Failed to recontact tracker {self._tracker_url}: {exc}")

    async def stop_contacting(self):
        task = self._recontact_task
        if task is None:
            return
        task.cancel()
        self._recontact_task = None
        await asyncio.gather(task, return_exceptions=True)

    