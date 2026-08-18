from typing import Optional
import peer_protocol_encoder as protocol_encoder

class PeerState:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.remote_peer_id: Optional[bytes] = None
        self.bitfield: Optional[bytes] = None
        
        self.am_choking = True
        self.am_interested = False
        
        self.peer_choking = True
        self.peer_interested = False

    def update_bitfield(self, bitfield: Optional[bytes]) -> None:
        self.bitfield = bitfield

    def set_piece_in_bitfield(self, piece_index: int) -> bytes:
        self.bitfield = protocol_encoder.set_piece_in_bitfield(self.bitfield, piece_index)
        return self.bitfield
    
    def get_bitfield(self) -> Optional[bytes]:
        return self.bitfield

    def set_am_choking(self, value: bool) -> None:
        self.am_choking = value

    def set_am_interested(self, value: bool) -> None:
        self.am_interested = value

    def set_peer_choking(self, value: bool) -> None:
        self.peer_choking = value

    def set_peer_interested(self, value: bool) -> None:
        self.peer_interested = value

    def is_peer_choking(self) -> bool:
        return self.peer_choking

    def is_am_interested(self) -> bool:
        return self.am_interested