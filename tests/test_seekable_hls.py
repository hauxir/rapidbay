"""Seekable HLS building blocks: keyframe indexes, fMP4 timestamp rewriting
and the VOD playlist layout. The ffmpeg side is exercised end to end against
real MKV/MP4 files outside the unit tests."""

import struct
import threading
import time

from app import fmp4, keyframes, seekable_hls
from app.seekable_hls import (
    Probe,
    build_vod_playlist,
    parse_segment_request,
    segment_boundaries,
)

# --- Matroska --------------------------------------------------------------


def _ebml_id(eid: int) -> bytes:
    return eid.to_bytes((eid.bit_length() + 7) // 8, "big")


def _ebml_size(n: int) -> bytes:
    return bytes([0x08]) + n.to_bytes(4, "big")  # 4-byte length + marker byte


def _el(eid: int, payload: bytes) -> bytes:
    return _ebml_id(eid) + _ebml_size(len(payload)) + payload


def _uint(eid: int, value: int) -> bytes:
    return _el(eid, value.to_bytes(4, "big"))


def _mkv(cue_times_ms: list[int], cues_at_end: bool = True) -> bytes:
    info = _el(0x1549A966, _uint(0x2AD7B1, 1_000_000))
    tracks = _el(0x1654AE6B, _el(0xAE, _uint(0xD7, 2) + _uint(0x83, 2)) + _el(0xAE, _uint(0xD7, 1) + _uint(0x83, 1)))
    cue_points = b"".join(
        _el(0xBB, _uint(0xB3, t) + _el(0xB7, _uint(0xF7, 1) + _uint(0xF1, 0))) for t in cue_times_ms
    )
    # An audio-only cue point must be ignored.
    cue_points += _el(0xBB, _uint(0xB3, 999_999) + _el(0xB7, _uint(0xF7, 2) + _uint(0xF1, 0)))
    cues = _el(0x1C53BB6B, cue_points)
    cluster = _el(0x1F43B675, b"\x00" * 300_000)  # pushes trailing Cues past the head read
    seekhead_len = len(_el(0x114D9B74, _el(0x4DBB, _el(0x53AB, _ebml_id(0x1C53BB6B)) + _uint(0x53AC, 0))))
    body_before_cues = info + tracks + cluster
    cues_pos = seekhead_len + len(body_before_cues)
    seekhead = _el(0x114D9B74, _el(0x4DBB, _el(0x53AB, _ebml_id(0x1C53BB6B)) + _uint(0x53AC, cues_pos)))
    segment_body = seekhead + body_before_cues + cues if cues_at_end else info + tracks + cues + cluster
    return _el(0x1A45DFA3, _uint(0x4286, 1)) + _el(0x18538067, segment_body)


def _reader(data: bytes):
    def read(offset: int, length: int) -> bytes:
        return data[offset:offset + length]
    return read


def test_mkv_keyframes_from_trailing_cues():
    data = _mkv([0, 4170, 10_010, 20_000])
    assert keyframes.mkv_keyframes(_reader(data)) == [0.0, 4.17, 10.01, 20.0]


def test_mkv_keyframes_from_leading_cues():
    data = _mkv([0, 5000], cues_at_end=False)
    assert keyframes.mkv_keyframes(_reader(data)) == [0.0, 5.0]


def test_mkv_without_cues_is_unseekable():
    data = _el(0x1A45DFA3, _uint(0x4286, 1)) + _el(0x18538067, _el(0x1F43B675, b"\x00" * 10))
    assert keyframes.mkv_keyframes(_reader(data)) is None


# --- MP4 ---------------------------------------------------------------------


def _box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def _full(kind: bytes, payload: bytes, version: int = 0) -> bytes:
    return _box(kind, bytes([version, 0, 0, 0]) + payload)


def _video_trak(timescale: int, deltas: int, n: int, sync: list[int], ctts_off: int, elst: bytes | None) -> bytes:
    stbl = _box(b"stbl", (
        _full(b"stts", struct.pack(">III", 1, n, deltas))
        + _full(b"stss", struct.pack(">I", len(sync)) + b"".join(struct.pack(">I", s) for s in sync))
        + _full(b"ctts", struct.pack(">III", 1, n, ctts_off))
    ))
    mdia = _box(b"mdia", (
        _full(b"mdhd", struct.pack(">IIII", 0, 0, timescale, n * deltas) + b"\x00" * 4)
        + _full(b"hdlr", struct.pack(">I", 0) + b"vide" + b"\x00" * 12)
        + _box(b"minf", stbl)
    ))
    edts = _box(b"edts", elst) if elst else b""
    return _box(b"trak", _full(b"tkhd", struct.pack(">IIII", 0, 0, 1, 0) + b"\x00" * 64) + edts + mdia)


def _mvhd(timescale: int) -> bytes:
    return _full(b"mvhd", struct.pack(">III", 0, 0, timescale) + b"\x00" * 84)


def test_mp4_keyframes_with_trailing_moov_and_edit_list():
    # 24 fps in a 12288 timescale, keyframe every 48 frames, B-frame delay of
    # 2 frames removed again by the edit list.
    elst = _full(b"elst", struct.pack(">I", 1) + struct.pack(">IiI", 0, 1024, 0x10000))
    moov = _box(b"moov", _mvhd(1000) + _video_trak(12288, 512, 240, [1, 49, 97, 145, 193], 1024, elst))
    data = _box(b"ftyp", b"isom\x00\x00\x02\x00") + _box(b"mdat", b"\x00" * 5000) + moov
    assert keyframes.mp4_keyframes(_reader(data), len(data)) == [0.0, 2.0, 4.0, 6.0, 8.0]


def test_mp4_keyframes_with_empty_edit():
    elst = _full(b"elst", struct.pack(">I", 2) + struct.pack(">IiI", 500, -1, 0x10000) + struct.pack(">IiI", 0, 0, 0x10000))
    moov = _box(b"moov", _mvhd(1000) + _video_trak(1000, 100, 30, [1, 11, 21], 0, elst))
    data = moov + _box(b"mdat", b"")
    assert keyframes.mp4_keyframes(_reader(data), len(data)) == [0.5, 1.5, 2.5]


# --- fMP4 rewriting ------------------------------------------------------------


def _init(elst_empty_ms: int, media_time: int) -> bytes:
    elst = _full(b"elst", struct.pack(">I", 2) + struct.pack(">IiI", elst_empty_ms, -1, 0x10000)
                 + struct.pack(">IiI", 0, media_time, 0x10000))
    trak = _box(b"trak", (
        _full(b"tkhd", struct.pack(">IIII", 0, 0, 1, 0) + b"\x00" * 64)
        + _box(b"edts", elst)
        + _box(b"mdia", _full(b"mdhd", struct.pack(">IIII", 0, 0, 12800, 0) + b"\x00" * 4)
               + _full(b"hdlr", struct.pack(">I", 0) + b"vide" + b"\x00" * 12))
    ))
    return _box(b"ftyp", b"iso6") + _box(b"moov", _mvhd(1000) + trak)


def _fragment(tfdt: int) -> bytes:
    traf = _box(b"traf", _full(b"tfhd", struct.pack(">I", 1)) + _full(b"tfdt", struct.pack(">Q", tfdt), version=1))
    return _box(b"styp", b"msdh") + _box(b"sidx", b"\x00" * 24) + _box(b"moof", _box(b"mfhd", b"\x00" * 8) + traf) + _box(b"mdat", b"x")


def test_jobs_land_on_one_timeline():
    # A job from the start and one started at 30s (as ffmpeg writes them with
    # -copyts -output_ts_offset 10): the same keyframe must get the same tfdt.
    from_start = fmp4.track_offsets(_init(10_000, 1024))
    from_seek = fmp4.track_offsets(_init(40_000, 1024))
    a, first_a = fmp4.rewrite_fragments(_fragment(384_000), from_start, keep_styp=False)
    b, first_b = fmp4.rewrite_fragments(_fragment(0), from_seek, keep_styp=False)
    assert first_a == first_b == {1: 510_976}
    assert a == b
    assert b"styp" not in a and b"sidx" not in a and a[4:8] == b"moof"


def test_canonical_init_has_no_edit_lists():
    a = fmp4.strip_edit_lists(_init(10_000, 1024))
    b = fmp4.strip_edit_lists(_init(40_000, 1024))
    assert a == b
    assert b"edts" not in a and b"elst" not in a
    assert fmp4.timescales(a) == {1: (12800, True)}


# --- playlist ------------------------------------------------------------------


def test_segments_group_keyframes():
    # The first segments are short so playback starts sooner.
    assert segment_boundaries([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30], 6) == [
        0, 2, 4, 6, 12, 18, 24, 30
    ]
    assert segment_boundaries([0, 10, 20, 30], 6) == [0, 10, 20, 30]
    assert segment_boundaries([0.5, 1.0, 3.7, 7.4, 11.1, 14.8, 18.5, 22.2, 25.9], 6) == [0.5, 3.7, 7.4, 11.1, 18.5, 25.9]


def test_vod_playlist_lists_every_segment():
    p = Probe(start_time=0, end_time=25.0, video_codec="h264", audio_codec="aac",
              boundaries=[0.0, 10.0, 20.0])
    playlist = build_vod_playlist("My Movie", p)
    assert "#EXT-X-PLAYLIST-TYPE:VOD" in playlist and playlist.rstrip().endswith("#EXT-X-ENDLIST")
    assert '#EXT-X-MAP:URI="My%20Movie_vod_init.mp4"' in playlist
    assert "#EXT-X-TARGETDURATION:10" in playlist
    assert [line for line in playlist.splitlines() if line.startswith("#EXTINF")] == [
        "#EXTINF:10.000000,", "#EXTINF:10.000000,", "#EXTINF:5.000000,"
    ]
    assert "My%20Movie_vod_2.m4s" in playlist


def test_parse_segment_request():
    assert parse_segment_request("Movie.2026_vod_12.m4s") == ("Movie.2026", 12)
    assert parse_segment_request("Movie.2026_vod_init.mp4") == ("Movie.2026", None)
    assert parse_segment_request("Movie.2026.mp4") is None
    assert parse_segment_request("Movie_vod_x.m4s") is None


def test_superseded_waiter_does_not_restart_the_job(tmp_path):
    streamer = seekable_hls.SeekableHLSStreamer()
    session = seekable_hls._Session(
        "h", "f.mkv", str(tmp_path), str(tmp_path / "f.m3u8"), "http://x", 1, "f.mkv", lambda: False
    )
    session.probe = seekable_hls.Probe(0.0, 60.0, "h264", "aac", [0.0, 10.0, 20.0, 30.0])
    started = []
    streamer._ensure_job = lambda _s, n: started.append(n)  # type: ignore[method-assign]
    result = []
    t = threading.Thread(target=lambda: result.append(streamer.wait_for(session, 1, 5)))
    t.start()
    while not started:
        time.sleep(0.01)
    # A seek elsewhere supersedes it while no job is running.
    with session.cond:
        session.request_seq += 1
        session.cond.notify_all()
    t.join(2)
    # It gives up instead of dragging ffmpeg back to its old position.
    assert result == [None]
    assert started == [1]
