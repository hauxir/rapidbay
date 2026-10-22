import threading
import urllib.error
import urllib.request

import pytest

from app import torrent_stream
from app.torrent_stream import parse_range


@pytest.mark.parametrize(("header", "expected"), [
    (None, (0, 99)),
    ("bytes=0-", (0, 99)),
    ("bytes=10-19", (10, 19)),
    ("bytes=90-200", (90, 99)),
    ("bytes=-10", (90, 99)),
    ("bytes=100-", None),
    ("bytes=20-10", None),
    ("bytes=-", None),
    ("items=0-1", None),
])
def test_parse_range(header, expected):
    assert parse_range(header, 100) == expected


def test_reads_wait_for_pieces_and_rush_a_growing_window(tmp_path):
    data = bytes(range(256)) * 64 * 1024  # 16 MiB
    path = tmp_path / "f.bin"
    path.write_bytes(data)
    available = threading.Event()
    rushes = []

    def downloaded(_mh, _fn, start, end):
        # Nothing past the first 1 MiB until the test releases it.
        return end <= 1024 * 1024 or available.is_set()

    server = torrent_stream.TorrentFileServer(
        locate=lambda _mh, _fn: (str(path), len(data)),
        is_range_downloaded=downloaded,
        rush=lambda _mh, _fn, start, end: rushes.append((start, end)),
        window_for=lambda _mh, _fn: 8 * 1024 * 1024,
    )
    server.start()
    try:
        timer = threading.Timer(0.3, available.set)
        timer.start()
        req = urllib.request.Request(server.url("a" * 40, "f.bin"), headers={"Range": "bytes=0-"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            assert resp.status == 206
            assert resp.headers["Content-Range"] == f"bytes 0-{len(data) - 1}/{len(data)}"
            assert resp.read() == data
    finally:
        server.stop()
    # Critical phase: a small first window that doubles as it is consumed, up
    # to the read-ahead size.
    sizes = [end - start for start, end in rushes]
    assert sizes[0] == torrent_stream.CRITICAL_WINDOW_BYTES
    assert sizes[:3] == [2 << 20, 4 << 20, 8 << 20]
    assert max(sizes) == 8 << 20


def test_rejects_wrong_token(tmp_path):
    server = torrent_stream.TorrentFileServer(
        locate=lambda _mh, _fn: (str(tmp_path / "x"), 1),
        is_range_downloaded=lambda *_: True,
        rush=lambda *_: None,
        window_for=lambda *_: 1,
    )
    server.start()
    try:
        url = server.url("a" * 40, "f.bin").replace(f":{server.port}/", f":{server.port}/wrong", 1)
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(url, timeout=5)
        assert e.value.code == 404
    finally:
        server.stop()
