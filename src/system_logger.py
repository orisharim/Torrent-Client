from datetime import datetime
from pathlib import Path


class SystemLogger:
    """Logger for events belonging to the running torrent client."""

    LOG_DIRECTORY = Path(__file__).resolve().parents[1] / "logs" / "system"
    PRINT_SYSTEM_MESSAGES = True
    LOG_SYSTEM_MESSAGES = True

    LOG_API_FILE = True
    LOG_TORRENTS_MANAGER_FILE = True
    LOG_PEERS_RECEIVER_FILE = True
    LOG_PORT_FORWARDER_FILE = True

    def __init__(self) -> None:
        self.file = None
        self.name: str | None = None

    def create_file(self, file_path: str | Path | None = None) -> None:
        if self.file:
            return
        name = f"system_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        log_directory = Path(file_path) if file_path else self.LOG_DIRECTORY
        log_directory.mkdir(parents=True, exist_ok=True)
        self.name = str(log_directory / name)
        try:
            self.file = open(self.name, "w", encoding="utf-8")
        except OSError as exc:
            self.print_system_message(f"Failed to create system log file: {exc}")
            self.file = None

    def get_log_path(self) -> str | None:
        """Return the path of the current system log, if one is open."""
        return self.name if self.file else None

    def log(self, message: str) -> None:
        if self.LOG_SYSTEM_MESSAGES and self.file:
            self.file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            self.file.flush()

    def _publish_message(self, message: str, enabled: bool = True) -> None:
        if not enabled:
            return
        self.print_system_message(message)
        self.log(message)

    @classmethod
    def print_system_message(cls, message: str) -> None:
        if cls.PRINT_SYSTEM_MESSAGES:
            print(message)

    def close(self) -> None:
        if self.file:
            self.file.close()
            self.file = None

    def log_by_file(self, file_name: str, message: str) -> None:
        file_logging = {
            "api": self.LOG_API_FILE,
            "torrents_manager": self.LOG_TORRENTS_MANAGER_FILE,
            "peers_receiver": self.LOG_PEERS_RECEIVER_FILE,
            "port_forwarder": self.LOG_PORT_FORWARDER_FILE,
        }
        if file_name in file_logging:
            self._publish_message(message, file_logging[file_name])
