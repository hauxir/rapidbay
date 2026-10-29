import os

from app import rapidbaydaemon, settings
from app.rapidbaydaemon import _read_ahead_window


def test_read_ahead_window_follows_bitrate():
    assert _read_ahead_window(None) == settings.HLS_PREFETCH_BYTES
    # Low bitrate: floor so there's still a useful buffer.
    assert _read_ahead_window(10_000) == 16 * 1024 * 1024
    # 5 MB/s (a 40 Mbit/s remux) for HLS_READ_AHEAD_SECONDS.
    assert _read_ahead_window(5_000_000) == 5_000_000 * settings.HLS_READ_AHEAD_SECONDS
    assert _read_ahead_window(10**9) == 1024 * 1024 * 1024



def test_forget_file_drops_every_record():
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)
    key = ("h", "movie.mkv")
    daemon.subtitle_downloads = {os.path.join(settings.DOWNLOAD_DIR, "h", "dir/movie.mkv"): "x"}
    daemon._file_poll_times = {key: 1.0}
    daemon._head_rushes = {key: 1.0}
    daemon._byte_rates = {key: 1}
    daemon._forget_file("h", "dir/movie.mkv")
    assert not daemon.subtitle_downloads and not daemon._file_poll_times and not daemon._head_rushes
    assert not daemon._byte_rates
