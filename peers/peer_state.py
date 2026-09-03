from typing import Optional
import peers.peer_protocol_encoder as protocol_encoder

class PeerState:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._peer_id: Optional[bytes] = None
        self._peer_bitfield: Optional[bytes] = None
        
        self._am_choking = True
        self._am_interested = False
        
        self._peer_choking = True
        self._peer_interested = False

        self._am_seeding = False

    def update_bitfield(self, bitfield: Optional[bytes]) -> None:
        self._peer_bitfield = bitfield

    def set_piece_in_bitfield(self, piece_index: int) -> bytes:
        self._peer_bitfield = protocol_encoder.set_piece_in_bitfield(self._peer_bitfield, piece_index)
        return self._peer_bitfield
    
    def get_bitfield(self) -> Optional[bytes]:
        return self._peer_bitfield

    def set_am_choking(self, value: bool) -> None:
        self._am_choking = value

    def set_am_interested(self, value: bool) -> None:
        self._am_interested = value

    def set_peer_choking(self, value: bool) -> None:
        self._peer_choking = value

    def set_peer_interested(self, value: bool) -> None:
        self._peer_interested = value

    def is_peer_choking(self) -> bool:
        return self._peer_choking

    def is_am_interested(self) -> bool:
        return self._am_interested

    def set_remote_peer_id(self, peer_id: bytes) -> None:
        self._peer_id = peer_id

    def get_remote_peer_id(self) -> Optional[bytes]:
        return self._peer_id
    
    def get_am_choking(self) -> bool:
        return self._am_choking

    def get_am_seeding(self) -> bool:
        return self._am_seeding

    def set_am_seeding(self, am_seeding: bool) -> None:
        self._am_seeding = am_seeding