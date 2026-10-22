import time

import libtorrent

from app import torrent
from app.torrent import LockManager, TorrentClient

PIECE = 16 * 1024


def _handle(tmp_path):
    src = tmp_path / "src"
    (src / "t").mkdir(parents=True)
    (src / "t" / "a.mkv").write_bytes(b"a" * 10 * PIECE)
    (src / "t" / "b.mkv").write_bytes(b"b" * (10 * PIECE + 100))
    fs = libtorrent.file_storage()
    libtorrent.add_files(fs, str(src / "t"))
    ct = libtorrent.create_torrent(fs, PIECE, flags=libtorrent.create_torrent.v1_only)
    libtorrent.set_piece_hashes(ct, str(src))
    ti = libtorrent.torrent_info(libtorrent.bencode(ct.generate()))
    ses = libtorrent.session({
        "listen_interfaces": "127.0.0.1:0",
        "enable_dht": False, "enable_lsd": False, "enable_upnp": False, "enable_natpmp": False,
    })
    h = ses.add_torrent({"ti": ti, "save_path": str(tmp_path / "dl")})
    return ses, h


def _wait(cond):
    deadline = time.monotonic() + 5
    while not cond():
        assert time.monotonic() < deadline
        time.sleep(0.02)


def test_clearing_deadlines_restores_file_piece_priorities(tmp_path):
    ses, h = _handle(tmp_path)
    torrent.prioritize_files(h, [0, 4])
    client = TorrentClient.__new__(TorrentClient)
    client.locks = LockManager()
    client.torrents = {"x": h}

    client.prioritize_byte_range("x", "b.mkv", 0, 3 * PIECE)
    _wait(lambda: list(h.get_piece_priorities())[10:13] == [7, 7, 7])

    client.clear_piece_deadlines("x")
    _wait(lambda: list(h.get_piece_priorities()) == [0] * 10 + [4] * 11)
    del ses
