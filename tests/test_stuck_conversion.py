import os
import time
import traceback

import pytest

from app import rapidbaydaemon, settings, torrent, video_conversion


def _age(path, hours):
    t = time.time() - hours * 3600
    os.utime(path, (t, t))


def test_cleanup_keeps_dirs_of_loaded_torrents(tmp_path):
    loaded, gone = tmp_path / "loaded", tmp_path / "gone"
    for d in (loaded, gone):
        d.mkdir()
        _age(d, 48)
    rapidbaydaemon._remove_old_files_and_directories(str(tmp_path), 10, keep={"loaded"})
    assert loaded.exists() and not gone.exists()


def test_conversion_failed_marker_roundtrip(tmp_path):
    out = str(tmp_path / "movie.mp4")
    assert not video_conversion.is_conversion_failed(out)
    open(out + ".failed", "w").close()
    assert video_conversion.is_conversion_failed(out)
    video_conversion.clear_conversion_failed(out)
    assert not video_conversion.is_conversion_failed(out)


def test_failed_conversion_is_marked(tmp_path, monkeypatch):
    out = str(tmp_path / "movie.mp4")

    class Failed:
        returncode = 1

        def wait(self):
            pass

    def fake_convert(_in, out_path, subtitle_filepaths=None):
        with open(out_path + settings.LOG_POSTFIX, "w") as f:
            f.write("100\rframe=1 time=00:00:01\rbad input\n")
        return Failed()

    monkeypatch.setattr(video_conversion, "_convert_file_to_mp4", fake_convert)
    logged = []
    monkeypatch.setattr(video_conversion.log, "write_log", lambda: logged.append(traceback.format_exc()))
    converter = video_conversion.VideoConverter()
    converter._run_conversion(str(tmp_path / "movie.mkv"), out).join()
    assert video_conversion.is_conversion_failed(out)
    assert len(logged) == 1 and "bad input" in logged[0]


def test_progress_ignores_trailing_error_lines(tmp_path):
    out = str(tmp_path / "movie.mp4")
    with open(out + settings.LOG_POSTFIX, "w") as f:
        f.write("100\rframe=1 time=00:00:50.00\rsome warning\n")
    assert video_conversion.get_conversion_progress(out) == 0.5


def test_magnet_metadata_timeout_removes_handle(monkeypatch):
    client = torrent.TorrentClient.__new__(torrent.TorrentClient)
    removed = []

    class Session:
        def remove_torrent(self, h):
            removed.append(h)

    client.session = Session()
    client.torrents = {}
    client.download_dir = "/nonexistent/"
    handle = object()
    monkeypatch.setattr(torrent.libtorrent, "add_magnet_uri", lambda *a: handle)

    def timeout(_h):
        raise TimeoutError("Metadata fetch timeout after 30 seconds")

    monkeypatch.setattr(torrent, "get_torrent_info", timeout)
    with pytest.raises(TimeoutError):
        client._add_magnet_link_to_downloads("magnet:?xt=urn:btih:" + "a" * 40)
    assert removed == [handle] and not client.torrents
