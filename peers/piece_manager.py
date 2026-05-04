import asyncio
from collections import deque
from asyncio import TaskGroup
from hashlib import sha1
import random
from typing import Optional

from peers.peer_connection import PeerConnection
from peers.piece import Piece
from peers.torrent_storage import TorrentStorage


class PieceManager:
    PIECES_AT_ONCE = 5
    CONNECTION_TIMEOUT = 10.0
    BLOCK_DOWNLOAD_TIMEOUT = 10.0
    MAX_IN_FLIGHT_BLOCKS = 6
    MAX_BLOCK_RETRIES = 3

    def __init__(
        self,
        peer_id: bytes,
        peers_info: list[tuple[str, int]],
        torrent_metadata,
    ) -> None:
        self.peers: list[PeerConnection] = []
        for ip, port in peers_info:
            self.peers.append(PeerConnection(ip, port, torrent_metadata.info_hash, peer_id))

        self.torrent_metadata = torrent_metadata
        self.peer_id = peer_id
        self.total_piece_count = len(torrent_metadata.pieces)

        self.bitfield: bytes = b""  # bitfield of pieces we have
        self.requested_pieces: set[int] = set()

        self.torrent_storage = TorrentStorage(
            piece_length=torrent_metadata.piece_length,
            total_piece_count=self.total_piece_count,
        )

        self.paused = False

    async def set_peers(self, peers_info: list[tuple[str, int]]) -> None:
        self.peers = []
        for ip, port in peers_info:
            self.peers.append(
                PeerConnection(ip, port, self.torrent_metadata.info_hash, self.peer_id)
            )

    async def add_peers(self, new_peers_info: list[tuple[str, int]]) -> None:
        for ip, port in new_peers_info:
            self.peers.append(
                PeerConnection(ip, port, self.torrent_metadata.info_hash, self.peer_id)
            )

    async def connect_to_unconnected_peers(self) -> None:
        async with TaskGroup() as tg:
            for peer in self.peers:
                # Connect only when a peer has not completed bitfield exchange yet.
                if peer.bitfield is not None:
                    continue
                tg.create_task(self._connect_to_peer(peer))

    async def connect_to_all_peers(self) -> None:
        await self.close_all()

        async with TaskGroup() as tg:
            for peer in self.peers:
                tg.create_task(self._connect_to_peer(peer))

    async def _connect_to_peer(self, peer: PeerConnection) -> None:
        if peer.bitfield is not None:
            return
        try:
            async with asyncio.timeout(self.CONNECTION_TIMEOUT):
                await peer.connect()
                await peer.send_handshake()
                await peer.read_bitfield()

        except Exception as e:
            print(f"Failed to connect to peer {peer.host}:{peer.port}: {e}")

    async def close_all(self) -> None:
        for peer in self.peers:
            await peer.close()

    async def pause_downloads(self) -> None:
        self.paused = True
        for peer in self.peers:
            if peer.interested:
                await peer.send_not_interested()

    async def resume_downloads(self) -> None:
        self.paused = False

    async def download_pieces(self) -> None:
        if self.paused:
            return
        async with TaskGroup() as tg:
            for _ in range(self.PIECES_AT_ONCE):
                tg.create_task(self._download_piece())

    async def _download_piece(self) -> Optional[Piece]:
        next_piece = await self._get_next_piece_index()
        if next_piece is None:
            return None

        piece_index, selected_peer = next_piece
        self.requested_pieces.add(piece_index)
        try:
            if self.paused:
                return None

            candidate_peers = [
                selected_peer,
                *[
                    peer
                    for peer in self.peers
                    if peer is not selected_peer
                    and peer.bitfield is not None
                    and not peer.choked
                    and self._has_piece(peer.bitfield, piece_index)
                ],
            ]

            for peer in candidate_peers:
                if self.paused:
                    return None
                piece = await self._download_piece_from_peer(piece_index, peer)
                if piece is not None:
                    return piece

            return None
        finally:
            self.requested_pieces.discard(piece_index)

    async def _download_piece_from_peer(self, piece_index: int, peer: PeerConnection) -> Optional[Piece]:
        if peer.choked:
            return None

        if not peer.interested:
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

            while pending and len(in_flight) < self.MAX_IN_FLIGHT_BLOCKS:
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
                # Requeue all inflight blocks on timeout to recover from dropped packets.
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

        ordered_blocks: list[tuple[int, int, bytes]] = [
            (piece_index, begin, received[begin])
            for begin in sorted(received.keys())
        ]
        piece = Piece(ordered_blocks)
        if not self._validate_piece(piece_index, piece):
            return None

        self.torrent_storage.add_piece(piece_index, piece)
        return piece

    async def _get_next_piece_index(self) -> Optional[tuple[int, PeerConnection]]:
        pieces_counts: list[tuple[int, int, list[PeerConnection]]] = []

        for idx in range(self.total_piece_count):
            if self._has_piece(self.bitfield, idx) or idx in self.requested_pieces or idx in self.torrent_storage.downloaded_pieces:
                continue

            count = 0
            peers_with_piece = []
            for peer in self.peers:
                if peer.choked or not peer.bitfield:
                    continue
                if self._has_piece(peer.bitfield, idx):
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
