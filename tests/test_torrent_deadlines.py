from app import torrent
from app.torrent import LockManager, TorrentClient


class _Files:
    def file_offset(self, _i):
        return 100  # the file starts 100 bytes into the torrent


class _Info:
    def files(self):
        return _Files()

    def piece_length(self):
        return 1000

    def num_pieces(self):
        return 10


class _File:
    size = 5000


class _Handle:
    def __init__(self, have=()):
        self._have = set(have)
        self.deadlines = {}
        self.priorities = {}

    def has_metadata(self):
        return True

    def get_torrent_info(self):
        return _Info()

    def have_piece(self, idx):
        return idx in self._have

    def piece_priority(self, idx, prio):
        self.priorities[idx] = prio

    def set_piece_deadline(self, idx, ms):
        self.deadlines[idx] = ms


def _client(h):
    client = TorrentClient.__new__(TorrentClient)
    client.locks = LockManager()
    client.torrents = {"h": h}
    return client


def test_deadlines_follow_playback_from_the_range_start(monkeypatch):
    monkeypatch.setattr(torrent, "get_index_and_file_from_files", lambda _h, _fn: (0, _File()))
    h = _Handle(have={2})
    # File bytes 950-3100 → torrent bytes 1050-3200 → pieces 1..3; piece 2
    # is on disk already and left alone.
    _client(h).prioritize_byte_range("h", "f.mkv", 950, 3100, byte_rate=1000)
    assert set(h.priorities) == {1, 3}
    # Piece 1 holds the range start: due now. Piece 3 starts 1950 bytes
    # past it: 1.95 s at 1000 B/s, not "two whole pieces" = 2 s.
    assert h.deadlines == {1: 0, 3: 1950}


def test_deadlines_without_a_bitrate_keep_ascending_order(monkeypatch):
    monkeypatch.setattr(torrent, "get_index_and_file_from_files", lambda _h, _fn: (0, _File()))
    h = _Handle()
    _client(h).prioritize_byte_range("h", "f.mkv", 0, 3000)
    assert [h.deadlines[i] for i in sorted(h.deadlines)] == [0, 10, 20, 30]
