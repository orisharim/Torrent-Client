from datetime import datetime
from pathlib import Path

class SessionLogger:

    PRINT_SESSION_MESSAGES = True
    LOG_SESSION_MESSAGES = True

    #specific stats to log
    LOG_INCOMING_MESSAGES = False
    LOG_RECEIVED_BLOCKS = True
    LOG_PEER_STATE_CHANGES = True
    LOG_IGNORED_BLOCKS = True
    LOG_BLOCK_REQUEST_FAILURES = True
    LOG_DOWNLOADED_PIECES = True
    LOG_UPLOADED_PIECES = True
    LOG_CONNECTION_AMOUNT = True
    LOG_PEER_PIECE_REQUESTS = True
    LOG_DOWNLOAD_SPEED = True
    LOG_UPLOAD_SPEED = True

    #files to log
    LOG_PEER_CONNECTION_FILE = True
    LOG_PEERS_FILE = True
    LOG_PEERS_RECEIVER_FILE = True
    LOG_PORT_FORWARDER_FILE = True
    LOG_TORRENT_SESSION_FILE = True
    LOG_TRACKER_FILES = True
    LOG_TORRENT_STORAGE_FILE = True

    def __init__(self, torrent_name: str):
        self.torrent_name = torrent_name
        self.file = None
        self.name = None

    def create_file(self, file_path: str) -> None:
        name = self.torrent_name.replace(" ", "_") + datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".log"
        Path(file_path).mkdir(parents=True, exist_ok=True)
        self.name = str(Path(file_path) / name)
        try:
            self.file = open(self.name, "w")
        except Exception as e:
            self.print_session_message(f"Failed to create log file: {e}")
            self.file = None

    def log(self, message: str) -> None:
        if self.LOG_SESSION_MESSAGES and self.file:
            self.file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            self.file.flush()

    def _publish_message(self, message: str, should_log: bool = True) -> None:
        self.print_session_message(message)
        if should_log:
            self.log(message)

    @classmethod
    def print_session_message(cls, message: str) -> None:
        if cls.PRINT_SESSION_MESSAGES:
            print(message)

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None

    def log_by_file(self, file_name: str, message: str) -> None:
        file_logging = {
            "peer_connection": self.LOG_PEER_CONNECTION_FILE,
            "peers": self.LOG_PEERS_FILE,
            "peers_receiver": self.LOG_PEERS_RECEIVER_FILE,
            "port_forwarder": self.LOG_PORT_FORWARDER_FILE,
            "torrent_session": self.LOG_TORRENT_SESSION_FILE,
            "tracker_client": self.LOG_TRACKER_FILES,
            "contact_tracker": self.LOG_TRACKER_FILES,
            "torrent_storage": self.LOG_TORRENT_STORAGE_FILE,
        }
        if file_name in file_logging:
            self._publish_message(message, file_logging[file_name])

    def log_incoming_message(self, message: str) -> None:
        self._publish_message(f"Received message {message}", self.LOG_INCOMING_MESSAGES)

    def log_received_block(self, piece: int, offset: int, size: int, total: str, peer: str) -> None:
        self._publish_message(
            f"Received block: piece {piece}, offset {offset}, size {size}, "
            f"total {total} from {peer}",
            self.LOG_RECEIVED_BLOCKS,
        )

    def log_peer_state_change(self, state: str, peer: str) -> None:
        self._publish_message(f"Peer {peer} {state}", self.LOG_PEER_STATE_CHANGES)

    def log_ignored_block(self, piece: int, offset: int, peer: str) -> None:
        self._publish_message(
            f"Ignoring unrequested block: piece {piece}, offset {offset} from {peer}",
            self.LOG_IGNORED_BLOCKS,
        )

    def log_block_request_failure(self, reason: str, piece: int, peer: str) -> None:
        if reason == "timed out":
            message = f"Timed out waiting for blocks of piece {piece} from {peer}"
        elif reason == "blocked because peer is choking":
            message = f"Request blocked because peer is choking: piece {piece} from {peer}"
        else:
            message = f"Block request {reason}: piece {piece} from {peer}"
        self._publish_message(message, self.LOG_BLOCK_REQUEST_FAILURES)

    def log_downloaded_piece(self, piece: int, peer: str) -> None:
        self._publish_message(
            f"From {peer} - Piece {piece} completed",
            self.LOG_DOWNLOADED_PIECES,
        )

    def log_uploaded_piece(self, piece: int, peer: str) -> None:
        self._publish_message(
            f"Uploaded piece {piece} to {peer}",
            self.LOG_UPLOADED_PIECES,
        )

    def log_connection_amount(self, amount: int, maximum: str, connecting: int, known: int) -> None:
        self._publish_message(
            f"Peers: {amount}/{maximum} connected, "
            f"{connecting} connecting, {known} known",
            self.LOG_CONNECTION_AMOUNT,
        )

    def log_peer_piece_request(self, piece: int, peer: str | None = None) -> None:
        if peer is None:
            message = f"Peer requested piece: {piece}"
        else:
            message = f"Requesting piece {piece} from {peer}"
        self._publish_message(message, self.LOG_PEER_PIECE_REQUESTS)

    def log_download_speed(self, megabytes: float) -> None:
        self._publish_message(
            f"Download speed: {megabytes:.2f} megabytes/second",
            self.LOG_DOWNLOAD_SPEED,
        )

    def log_upload_speed(self, megabytes: float) -> None:
        self._publish_message(
            f"Upload speed: {megabytes:.2f} megabytes/second",
            self.LOG_UPLOAD_SPEED,
        )
