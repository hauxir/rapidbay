# Local development stub for libtorrent
# This allows linting/type checking without the actual library

from typing import Any

class TorrentHandle:
    def has_metadata(self) -> bool:
        return True

    def get_torrent_info(self) -> TorrentInfo:
        return TorrentInfo()

    def status(self) -> TorrentStatus:
        return TorrentStatus()

    def file_priorities(self) -> list[int]:
        return []

    def prioritize_files(self, priorities: list[int]) -> None:
        pass


class TorrentInfo:
    def files(self) -> list[FileEntry]:
        return []

    def name(self) -> str:
        return ""


class FileEntry:
    def __init__(self):
        self.path = ""
        self.size = 0


class TorrentStatus:
    def __init__(self):
        self.state = 0
        self.progress = 0.0


class Session:
    def __init__(self):
        pass

    def add_torrent(self, params: Any) -> TorrentHandle:
        return TorrentHandle()

    def listen_on(self, start_port: int, end_port: int) -> None:
        pass

    def add_dht_router(self, router: str, port: int) -> None:
        pass

    def start_dht(self) -> None:
        pass

    def remove_torrent(self, handle: TorrentHandle) -> None:
        pass


# Mock common libtorrent functions and constants
def add_torrent_params() -> dict[str, Any]:
    return {}

def session() -> Session:
    return Session()

def torrent_info(filepath: str) -> Any:
    return Any

def add_magnet_uri(session: Session, magnet_link: str, params: dict[str, Any]) -> TorrentHandle:
    return TorrentHandle()


# Common state constants
state_downloading = 3
state_seeding = 5
