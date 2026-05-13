import asyncio
from collections import deque
from asyncio import TaskGroup
import random
from typing import Optional
from hashlib import sha1
import random
from typing import Optional

from peers.peer_connection import PeerConnection
from peers.piece import Piece
from peers.torrent_storage import TorrentStorage


class PieceManager:
    CONNECTION_TIMEOUT = 10.0
    RECEIVE_BITFIELD_CHECK_INTERVAL = 1.0
    
    BLOCK_DOWNLOAD_TIMEOUT = 10.0

    MAX_IN_FLIGHT_PIECES_PER_PEER = 5
    
    MAX_IN_FLIGHT_BLOCKS_PER_PIECE = 6
    MAX_BLOCK_RETRIES = 3

    def __init__( self, peer_id: bytes, peers_info: list[tuple[str, int]], torrent_metadata, download_path: str) -> None:
        self.torrent_metadata = torrent_metadata
        self.peer_id = peer_id
        self.total_piece_count = len(torrent_metadata.pieces)

        self.bitfield: bytes = b""  # bitfield of pieces we have
        self.requested_pieces: set[int] = set()

        self._requested_pieces_lock = asyncio.Lock()
        self._peers_lock = asyncio.Lock()
        self._bitfield_lock = asyncio.Lock()
        self._peer_pending_lock = asyncio.Lock()
        self.peer_pending_pieces: dict[PeerConnection, set[int]] = {}

        self.torrent_storage = TorrentStorage(
            piece_length = torrent_metadata.piece_length,
            total_piece_count = self.total_piece_count,
            files=torrent_metadata.files,
            base_path=download_path,
        )

        self.peers: list[PeerConnection] = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, torrent_metadata.info_hash, peer_id, self.torrent_storage))

        self.is_downloading = False

    async def set_peers(self, peers_info: list[tuple[str, int]]) -> None:
        async with self._peers_lock:
            self.peers = []
            for ip, port in peers_info:
                self.peers.append(PeerConnection(ip, port, self.torrent_metadata.info_hash, self.peer_id, self.torrent_storage))

    async def add_peers(self, new_peers_info: list[tuple[str, int]]) -> None:
        async with self._peers_lock:
            for ip, port in new_peers_info:
                self.peers.append(PeerConnection(ip, port, self.torrent_metadata.info_hash, self.peer_id, self.torrent_storage))

    async def connect_to_unconnected_peers(self) -> None:
        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        async with TaskGroup() as tg:
            for peer in peers_snapshot:
                #connect only when a peer has not completed bitfield exchange yet
                if await peer.get_bitfield() is not None:
                    continue
                tg.create_task(self._connect_to_peer(peer))

    async def connect_to_all_peers(self) -> None:
        await self.close_all()

        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        async with TaskGroup() as tg:
            for peer in peers_snapshot:
                tg.create_task(self._connect_to_peer(peer))

    async def _connect_to_peer(self, peer: PeerConnection) -> None:
        if await peer.get_bitfield() is not None:
            return
        try:
            async with asyncio.timeout(self.CONNECTION_TIMEOUT):
                await peer.connect()
                await peer.send_handshake()
                await peer.start_message_loop()
                while (await peer.get_bitfield()) is None: # wait for bitfield
                    await asyncio.sleep(self.RECEIVE_BITFIELD_CHECK_INTERVAL)
        
        except Exception as e:
            print(f"Failed to connect to peer {peer.host}:{peer.port}: {e}")

    async def close_all(self) -> None:
        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        for peer in peers_snapshot:
            await peer.close()        
    
    async def pause_downloads(self) -> None:
        self.is_downloading = True
        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        for peer in peers_snapshot:
            if await peer.is_interested():
                await peer.send_not_interested()

    async def resume_downloads(self) -> None:
        self.is_downloading = False

    async def _download_piece(self) -> Optional[Piece]:
        while not self.is_downloading:
            next_piece_idx = await self._reserve_next_piece()
            if next_piece_idx is None:
                return None

            async with self._peers_lock:
                peers_snapshot = list(self.peers)

            try:
                peers_with_piece = []
                for peer in peers_snapshot:
                    peer_bitfield = await peer.get_bitfield()
                    if peer_bitfield is None:
                        continue

                    if not await peer.is_choked():
                        if self._check_bitfield_has_piece(peer_bitfield, next_piece_idx):
                            peers_with_piece.append(peer)

                if not peers_with_piece:
                    return None

                tried_any = False
                for peer in peers_with_piece:
                    if self.is_downloading:
                        return None

                    # check and reserve per peer pending pieces
                    async with self._peer_pending_lock:
                        pending_set = self.peer_pending_pieces.get(peer)
                        if pending_set is None:
                            pending_set = set()
                            self.peer_pending_pieces[peer] = pending_set
                        # skip if this peer is already being asked for this piece
                        if next_piece_idx in pending_set:
                            continue
                        # enforce per peer concurrent pieces limit
                        if len(pending_set) >= self.MAX_IN_FLIGHT_PIECES_PER_PEER:
                            continue
                        pending_set.add(next_piece_idx)
                        tried_any = True

                    try:
                        piece = await self._download_piece_from_peer(next_piece_idx, peer)
                        if piece is not None:
                            return piece
                    finally:
                        async with self._peer_pending_lock:
                            s = self.peer_pending_pieces.get(peer)
                            if s:
                                s.discard(next_piece_idx)
                                if not s:
                                    # avoid growth of the dict
                                    del self.peer_pending_pieces[peer]

                # if no peer was attempted (all were busy/duplicated), treat as no available peer
                if not tried_any:
                    return None
            finally:
                async with self._requested_pieces_lock:
                    self.requested_pieces.discard(next_piece_idx)
        
    async def _download_piece_from_peer(self, piece_index: int, peer: PeerConnection) -> Optional[Piece]:
        if await peer.is_choked():
            return None

        if not await peer.is_interested():
            await peer.send_interested()

        piece_length = self._get_piece_length(piece_index)
        expected_lengths = {
            begin: min(PeerConnection.DEFAULT_BLOCK_LENGTH, piece_length - begin)
            for begin in range(0, piece_length, PeerConnection.DEFAULT_BLOCK_LENGTH)
        }

        pending = deque(expected_lengths)
        in_flight: set[int] = set()
        retries = {begin: 0 for begin in expected_lengths}
        received: dict[int, bytes] = {}

        while len(received) < len(expected_lengths):
            if self.is_downloading:
                await peer.send_not_interested()
                return None

            while pending and len(in_flight) < self.MAX_IN_FLIGHT_BLOCKS_PER_PIECE:
                begin = pending.popleft()
                if begin in received:
                    continue
                await peer.request_block(piece_index, begin, expected_lengths[begin])
                in_flight.add(begin)

            if not in_flight:
                return None

            try:
                async with asyncio.timeout(self.BLOCK_DOWNLOAD_TIMEOUT):
                    block_index, block_begin, block = await peer.read_block()
            except TimeoutError:
                timed_out_blocks = tuple(in_flight)
                in_flight.clear()
                for begin in timed_out_blocks:
                    retries[begin] += 1
                    if retries[begin] > self.MAX_BLOCK_RETRIES:
                        return None
                    pending.appendleft(begin)
                continue

            if block_index != piece_index:
                continue
            if block_begin not in expected_lengths:
                continue

            in_flight.discard(block_begin)
            expected_length = expected_lengths[block_begin]
            if len(block) != expected_length:
                retries[block_begin] += 1
                if retries[block_begin] > self.MAX_BLOCK_RETRIES:
                    return None
                pending.append(block_begin)
                continue

            received[block_begin] = block

        ordered_blocks: list[tuple[int, int, bytes]] = []
        for begin in sorted(received.keys()):
            ordered_blocks.append((piece_index, begin, received[begin]))
       
        piece = Piece(ordered_blocks)
        if not self._validate_piece(piece_index, piece):
            return None

        await self.torrent_storage.add_piece(piece_index, piece)
        async with self._bitfield_lock:
            self.bitfield = self._set_piece_in_bitfield(self.bitfield, piece_index)
        return piece

    # reserves the next piece to download (rarest first) and return its index
    async def _reserve_next_piece(self) -> Optional[int]:
        while True:
            async with self._peers_lock:
                peers_snapshot = list(self.peers)
            async with self.torrent_storage._downloaded_pieces_lock:
                downloaded_pieces_snapshot = set(self.torrent_storage.downloaded_pieces.keys())
            async with self._requested_pieces_lock:
                requested_pieces_snapshot = set(self.requested_pieces)
            async with self._bitfield_lock:
                our_bitfield_snapshot = self.bitfield

            peers_bitfields: dict[PeerConnection, bytes] = {}
            for peer in peers_snapshot:
                peer_bitfield = await peer.get_bitfield()
                if peer_bitfield is not None:
                    peers_bitfields[peer] = peer_bitfield

            pieces_counts: dict[int, int] = {}
            for piece_index in range(self.total_piece_count):
                if self._check_bitfield_has_piece(our_bitfield_snapshot, piece_index):
                    continue
                if piece_index in requested_pieces_snapshot:
                    continue
                if piece_index in downloaded_pieces_snapshot:
                    continue

                count = 0
                for peer in peers_snapshot:
                    peer_bitfield = peers_bitfields.get(peer)
                    if peer_bitfield is None:
                        continue
                    if self._check_bitfield_has_piece(peer_bitfield, piece_index):
                        count += 1

                if count > 0:
                    pieces_counts[piece_index] = count

            if not pieces_counts:
                return None

            rarest_count = min(pieces_counts.values())
            rarest_pieces = [
                piece_index
                for piece_index, count in pieces_counts.items()
                if count == rarest_count
            ]

            chosen_piece = random.choice(rarest_pieces)
            async with self._requested_pieces_lock:
                if chosen_piece in self.requested_pieces:
                    continue
                self.requested_pieces.add(chosen_piece)
                return chosen_piece
                    

    # takes a bitfield and a piece idx and returns whether the bitfield indicates
    # that the piece is there (works for us or for remote peers)
    def _check_bitfield_has_piece(self, bitfield: bytes, piece_index: int) -> bool:
        byte_index = piece_index // 8
        if byte_index < 0 or byte_index >= len(bitfield):
            return False

        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)
        return (bitfield[byte_index] & mask) != 0
    
    def _set_piece_in_bitfield(self, bitfield: bytes, piece_index: int) -> bytes:
        byte_index = piece_index // 8
        bit_offset = piece_index % 8
        mask = 1 << (7 - bit_offset)

        if byte_index >= len(bitfield):
            bitfield += b'\x00' * (byte_index - len(bitfield) + 1)

        return (
            bitfield[:byte_index] +
            bytes([bitfield[byte_index] | mask]) +
            bitfield[byte_index + 1:]
        )

    def _validate_piece(self, piece_index: int, piece: Piece) -> bool:
        assembled_piece = piece.get_assembled_data()
        piece_hash = sha1(assembled_piece).digest()
        if piece_index < 0 or piece_index >= self.total_piece_count:
            return False

        expected_hash = self.torrent_metadata.pieces[piece_index]
        return piece_hash == expected_hash

    def _get_piece_length(self, piece_index: int) -> int:
        default_piece_length = self.torrent_metadata.piece_length
        if piece_index < 0 or piece_index >= self.total_piece_count:
            return default_piece_length

        if piece_index < self.total_piece_count - 1:
            return default_piece_length

        total_length = self.torrent_metadata.length
        if total_length is None:
            return default_piece_length

        last_piece_length = total_length - (
            default_piece_length * (self.total_piece_count - 1)
        )
        if last_piece_length <= 0:
            return default_piece_length

        return last_piece_length

