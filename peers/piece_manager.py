import asyncio
from collections import deque
from asyncio import TaskGroup
from hashlib import sha1
import random
import time
from typing import Optional

from peers.peer_connection import PeerConnection
from peers.piece import Piece
from peers.torrent_storage import TorrentStorage


class PieceManager:
    CONNECTION_TIMEOUT = 10.0
    RECEIVE_BITFIELD_CHECK_INTERVAL = 1.0
    
    BLOCK_DOWNLOAD_TIMEOUT = 10.0

    
    MAX_IN_FLIGHT_PIECES = 5
    
    MAX_IN_FLIGHT_BLOCKS = 6
    MAX_BLOCK_RETRIES = 3

    def __init__( self, peer_id: bytes, peers_info: list[tuple[str, int]], torrent_metadata,) -> None:
        self.peers: list[PeerConnection] = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, torrent_metadata.info_hash, peer_id))

        self.torrent_metadata = torrent_metadata
        self.peer_id = peer_id
        self.total_piece_count = len(torrent_metadata.pieces)

        self.bitfield: bytes = b""  # bitfield of pieces we have
        self.requested_pieces: set[int] = set()
        self._requested_pieces_lock = asyncio.Lock()
        self._peers_lock = asyncio.Lock()
        self._bitfield_lock = asyncio.Lock()

        self.torrent_storage = TorrentStorage(
            piece_length=torrent_metadata.piece_length,
            total_piece_count=self.total_piece_count,
        )

        self.paused = False

    async def set_peers(self, peers_info: list[tuple[str, int]]) -> None:
        async with self._peers_lock:
            self.peers = []
            for ip, port in peers_info:
                self.peers.append(PeerConnection(ip, port, self.torrent_metadata.info_hash, self.peer_id))

    async def add_peers(self, new_peers_info: list[tuple[str, int]]) -> None:
        async with self._peers_lock:
            for ip, port in new_peers_info:
                self.peers.append(PeerConnection(ip, port, self.torrent_metadata.info_hash, self.peer_id))

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
                peer.set_request_handler(self._handle_peer_request)
        
        except Exception as e:
            print(f"Failed to connect to peer {peer.host}:{peer.port}: {e}")

    async def close_all(self) -> None:
        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        for peer in peers_snapshot:
            await peer.close()        
    
    async def pause_downloads(self) -> None:
        self.paused = True
        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        for peer in peers_snapshot:
            if await peer.is_interested():
                await peer.send_not_interested()

    async def resume_downloads(self) -> None:
        self.paused = False

    async def download_pieces(self) -> None:
        if self.paused:
            return
        async with TaskGroup() as tg:
            for _ in range(self.MAX_IN_FLIGHT_PIECES):
                tg.create_task(self._download_piece())

    async def _download_piece(self) -> Optional[Piece]:
        next_piece = await self._reserve_next_piece_index()
        if next_piece is None:
            return None

        piece_index, selected_peer = next_piece
        try:
            if self.paused:
                return None

            candidate_peers = [selected_peer]
            async with self._peers_lock:
                peers_snapshot = list(self.peers)
            for peer in peers_snapshot:
                if peer is selected_peer:
                    continue
                peer_bitfield = await peer.get_bitfield()
                if (
                    peer_bitfield is None
                ):
                    continue
                if not await peer.is_choked():
                    if self._has_piece(peer_bitfield, piece_index):
                        candidate_peers.append(peer)

            for peer in candidate_peers:
                if self.paused:
                    return None
                piece = await self._download_piece_from_peer(piece_index, peer)
                if piece is not None:
                    return piece

            return None
        finally:
            async with self._requested_pieces_lock:
                self.requested_pieces.discard(piece_index)

    async def _download_piece_from_peer(self, piece_index: int, peer: PeerConnection) -> Optional[Piece]:
        if await peer.is_choked():
            return None

        if not await peer.is_interested():
            await peer.send_interested()

        piece_length = self._get_piece_length(piece_index)
        expected_lengths: dict[int, int] = {}
        for begin in range(0, piece_length, PeerConnection.DEFAULT_BLOCK_LENGTH):
            expected_lengths[begin] = min(
                PeerConnection.DEFAULT_BLOCK_LENGTH,
                piece_length - begin,
            )

        pending = deque(expected_lengths.keys())
        in_flight: set[int] = set()
        retries: dict[int, int] = {begin: 0 for begin in expected_lengths}
        received: dict[int, bytes] = {}

        while len(received) < len(expected_lengths):
            if self.paused:
                await peer.send_not_interested()
                return None

            #request all possible blocks
            while pending and len(in_flight) < self.MAX_IN_FLIGHT_BLOCKS:
                begin = pending.popleft()
                if begin in received:
                    continue
                await peer.request_block(piece_index, begin, expected_lengths[begin])
                in_flight.add(begin)

            if not in_flight:
                return None

            #receive block
            try:
                async with asyncio.timeout(self.BLOCK_DOWNLOAD_TIMEOUT):
                    block_index, block_begin, block = await peer.read_block()
            except TimeoutError:
                # requeue all inflight blocks on timeout to recover from dropped packets
                timed_out_blocks = list(in_flight)
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

    async def _reserve_next_piece_index(self) -> Optional[tuple[int, PeerConnection]]:
        pieces_counts: list[tuple[int, int, list[PeerConnection]]] = []

        async with self._peers_lock:
            peers_snapshot = list(self.peers)
        async with self.torrent_storage._downloaded_pieces_lock:
            downloaded_pieces_snapshot = set(self.torrent_storage.downloaded_pieces.keys())

        async with self._requested_pieces_lock:
            async with self._bitfield_lock:
                our_bitfield_snapshot = self.bitfield
            for idx in range(self.total_piece_count):
                if self._has_piece(our_bitfield_snapshot, idx) or idx in self.requested_pieces or idx in downloaded_pieces_snapshot:
                    continue

                count = 0
                peers_with_piece = []
                for peer in peers_snapshot:
                    peer_bitfield = await peer.get_bitfield()
                    if not peer_bitfield:
                        continue
                    if self._has_piece(peer_bitfield, idx):
                        count += 1
                        peers_with_piece.append(peer)

                if count > 0:
                    pieces_counts.append((idx, count, peers_with_piece))

            if not pieces_counts:
                return None

            min_count = pieces_counts[0][1]
            for _, count, _ in pieces_counts:
                if count < min_count:
                    min_count = count

            rarest_pieces: list[tuple[int, list[PeerConnection]]] = []
            for idx, count, peer_connections in pieces_counts:
                if min_count == count:
                    rarest_pieces.append((idx, peer_connections))

            chosen_piece = random.choice(rarest_pieces)
            chosen_peer = random.choice(chosen_piece[1])
            self.requested_pieces.add(chosen_piece[0])
            return chosen_piece[0], chosen_peer

    # takes a bitfield and a piece idx and returns whether the bitfield indicates
    # that the piece is there (works for us or for remote peers)
    def _has_piece(self, bitfield: bytes, piece_index: int) -> bool:
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

    async def _handle_peer_request(self, peer: PeerConnection, piece_index: int, begin: int, length: int) -> None:
        if piece_index < 0 or piece_index >= self.total_piece_count:
            return

        piece_length = self._get_piece_length(piece_index)
        if begin < 0 or begin >= piece_length:
            return

        if length <= 0:
            return
        read_length = min(length, piece_length - begin)

        data = self.torrent_storage.read_piece_bytes(piece_index, begin, read_length)
        if data is None:
            return

        if await peer.is_choked():
            return

        await peer.send_piece(piece_index, begin, data)
