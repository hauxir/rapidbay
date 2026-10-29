import os

from app import rapidbaydaemon, settings
from app.rapidbaydaemon import _read_ahead_window


def test_stop_hls_under_stops_both_streamers(tmp_path):
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)
    stopped = []

    class Streamer:
        def __init__(self, name):
            self.name = name

        def stop_under(self, output_dir):
            stopped.append((self.name, output_dir))

    daemon.hls_streamer = Streamer("sequential")  # type: ignore[assignment]
    daemon.seekable_streamer = Streamer("seekable")  # type: ignore[assignment]
    daemon._stop_hls_under(str(tmp_path))
    assert stopped == [("sequential", str(tmp_path)), ("seekable", str(tmp_path))]


def test_read_ahead_window_follows_bitrate():
    assert _read_ahead_window(None) == settings.HLS_PREFETCH_BYTES
    # Low bitrate: floor so there's still a useful buffer.
    assert _read_ahead_window(10_000) == 16 * 1024 * 1024
    # 5 MB/s (a 40 Mbit/s remux) for HLS_READ_AHEAD_SECONDS.
    assert _read_ahead_window(5_000_000) == 5_000_000 * settings.HLS_READ_AHEAD_SECONDS
    assert _read_ahead_window(10**9) == 1024 * 1024 * 1024


def test_seekable_only_for_indexed_containers(tmp_path):
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)
    m3u8 = str(tmp_path / "x.m3u8")
    assert daemon._uses_seekable_hls("Movie.mkv", m3u8)
    assert daemon._uses_seekable_hls("Movie.MP4", m3u8)
    assert not daemon._uses_seekable_hls("Movie.avi", m3u8)
    with open(m3u8 + ".noseek", "w"):
        pass
    assert not daemon._uses_seekable_hls("Movie.mkv", m3u8)
    os.remove(m3u8 + ".noseek")


class _Status:
    def __init__(self, rate):
        self.download_rate = rate


class _Handle:
    def __init__(self, rate, size=100, have=0):
        self.rate = rate
        self.limit = -1
        self.size = size
        self.have = have

    def status(self):
        return _Status(self.rate)

    def has_metadata(self):
        return True

    def file_progress(self):
        return [self.have]

    def set_download_limit(self, limit):
        self.limit = limit


def _bandwidth_daemon(monkeypatch, torrents, polls, byte_rates):
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)

    class Client:
        pass

    daemon.torrent_client = Client()  # type: ignore[assignment]
    daemon.torrent_client.torrents = torrents  # type: ignore[attr-defined]
    daemon._file_poll_times = polls
    daemon._byte_rates = byte_rates
    daemon._throttled = set()
    daemon._link_peak = 0.0

    class File:
        def __init__(self, size):
            self.size = size

    monkeypatch.setattr(
        rapidbaydaemon.torrent, "get_index_and_file_from_files", lambda h, _fn: (0, File(h.size))
    )
    return daemon


def test_watched_download_gets_headroom(monkeypatch):
    import time

    watched, other = _Handle(rate=1_000_000), _Handle(rate=3_000_000)
    daemon = _bandwidth_daemon(
        monkeypatch,
        {"w": watched, "o": other},
        {("w", "movie.mkv"): time.monotonic()},
        {("w", "movie.mkv"): 1_000_000},
    )
    daemon._share_bandwidth()
    # Link peak 4 MB/s; the watched file needs 1.5 MB/s (1.5x its bitrate) and
    # gets 1 MB/s plus room to grow, capped at that need. The rest goes to the
    # other torrent.
    assert daemon._link_peak == 4_000_000
    assert other.limit == 4_000_000 - 1_500_000

    # A watched torrent held back by its own swarm only keeps what it uses
    # plus headroom, so the link isn't left idle.
    watched.rate = 200_000
    daemon._share_bandwidth()
    assert other.limit == int(daemon._link_peak) - (250_000 + 256 * 1024)
    assert watched.limit == -1
    assert daemon._throttled == {"o"}

    # Nobody watching any more: limits are lifted.
    daemon._file_poll_times.clear()
    daemon._share_bandwidth()
    assert other.limit == settings.TORRENT_DOWNLOAD_LIMIT
    assert daemon._throttled == set()


def test_finished_watched_file_does_not_throttle(monkeypatch):
    import time

    watched, other = _Handle(rate=0, size=100, have=100), _Handle(rate=3_000_000)
    daemon = _bandwidth_daemon(
        monkeypatch,
        {"w": watched, "o": other},
        {("w", "movie.mkv"): time.monotonic()},
        {},
    )
    daemon._share_bandwidth()
    assert other.limit == -1


def test_resume_picks_the_video_not_a_sidecar_with_the_same_stem(monkeypatch):
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)

    class File:
        def __init__(self, path):
            self.path = path

    class Info:
        def files(self):
            return [File("Movie/Movie.2024.jpg"), File("Movie/Movie.2024.srt"), File("Movie/Movie.2024.mkv")]

    class Handle:
        def has_metadata(self):
            return True

    class Client:
        torrents = {"h": Handle()}

    daemon.torrent_client = Client()  # type: ignore[assignment]
    monkeypatch.setattr(rapidbaydaemon.torrent, "get_torrent_info", lambda _h: Info())
    assert daemon._filename_for_stem("h", "Movie.2024") == "Movie.2024.mkv"
    assert daemon._filename_for_stem("h", "Other") is None


def test_bandwidth_sharing_survives_a_removed_watched_handle(monkeypatch):
    import time

    class Gone(_Handle):
        def status(self):
            raise RuntimeError("invalid torrent handle used")

    watched, other = Gone(rate=0), _Handle(rate=3_000_000)
    daemon = _bandwidth_daemon(
        monkeypatch,
        {"w": watched, "o": other},
        {("w", "movie.mkv"): time.monotonic()},
        {("w", "movie.mkv"): 1_000_000},
    )
    daemon._share_bandwidth()
    # The unreadable watched torrent counts as idle (headroom only); the
    # other one still gets a limit rather than the tick aborting.
    assert daemon._throttled == {"o"}
    assert other.limit == 3_000_000 - 256 * 1024


def test_forget_file_drops_every_record():
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)
    key = ("h", "movie.mkv")
    daemon.subtitle_downloads = {os.path.join(settings.DOWNLOAD_DIR, "h", "dir/movie.mkv"): "x"}
    daemon._file_poll_times = {key: 1.0}
    daemon._head_rushes = {key: 1.0}
    daemon._byte_rates = {key: 1}
    daemon._sequential_pending = {key}
    daemon._forget_file("h", "dir/movie.mkv")
    assert not daemon.subtitle_downloads and not daemon._file_poll_times and not daemon._head_rushes
    assert not daemon._byte_rates and not daemon._sequential_pending
