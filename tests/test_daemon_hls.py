import os
import threading
import time

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
    daemon._probe_attempts = {key: 1.0}
    daemon._forget_file("h", "dir/movie.mkv")
    assert not daemon.subtitle_downloads and not daemon._file_poll_times and not daemon._head_rushes
    assert not daemon._byte_rates and not daemon._probe_attempts


def _probe_daemon():
    daemon = rapidbaydaemon.RapidBayDaemon.__new__(rapidbaydaemon.RapidBayDaemon)
    daemon._byte_rates = {}
    daemon._probing = set()
    daemon._probe_attempts = {}
    daemon._probe_lock = threading.Lock()
    return daemon


def test_bitrate_probe_runs_once_at_a_time_and_retries_after_an_interval(monkeypatch):
    daemon = _probe_daemon()
    release = threading.Event()
    calls = []

    def slow_probe(_path):
        calls.append(1)
        release.wait(5)
        return None  # a sparse file: nothing yet

    monkeypatch.setattr(rapidbaydaemon, "_probe_duration", slow_probe)
    key = ("h", "movie.mkv")
    daemon._probe_byte_rate(key, "/x/movie.mkv", 1000)
    daemon._probe_byte_rate(key, "/x/movie.mkv", 1000)  # concurrent start: no second ffprobe
    release.set()
    while daemon._probing:
        time.sleep(0.01)
    assert calls == [1] and key not in daemon._byte_rates
    # Failed: not retried until the interval has passed...
    daemon._probe_byte_rate(key, "/x/movie.mkv", 1000)
    assert calls == [1]
    # ...then it is, and a duration now yields a rate.
    daemon._probe_attempts[key] -= rapidbaydaemon._PROBE_RETRY_INTERVAL
    monkeypatch.setattr(rapidbaydaemon, "_probe_duration", lambda _p: 10.0)
    daemon._probe_byte_rate(key, "/x/movie.mkv", 1000)
    while daemon._probing:
        time.sleep(0.01)
    assert daemon._byte_rates[key] == 100


def test_bitrate_probe_skips_containers_without_a_header_duration(monkeypatch):
    daemon = _probe_daemon()
    monkeypatch.setattr(rapidbaydaemon, "_probe_duration", lambda _p: 10.0)
    daemon._probe_byte_rate(("h", "movie.ts"), "/x/movie.ts", 1000)
    assert not daemon._probing and not daemon._probe_attempts
