"""Tests for the MP4 layout probe and faststart remux used by HLS early
playback (video_conversion._mp4_head_layout / build_faststart_preamble).

Builds a minimal synthetic ISO-BMFF file: ftyp, mdat, then a trailing moov
containing one stco chunk-offset table — the moov-at-end layout the remux
exists to handle.
"""

import struct

import pytest

from app.video_conversion import (
    _mp4_head_layout,
    build_faststart_preamble,
    is_pipe_streamable,
    mp4_remux_layout,
)


def _box(box_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def _stco(offsets: list[int]) -> bytes:
    body = (
        struct.pack(">I", 0)  # version/flags
        + struct.pack(">I", len(offsets))
        + b"".join(struct.pack(">I", o) for o in offsets)
    )
    return _box(b"stco", body)


FTYP = _box(b"ftyp", b"isom\x00\x00\x02\x00isomiso2")
MDAT = _box(b"mdat", bytes(range(256)) * 40)
MDAT_START = len(FTYP)
MDAT_END = MDAT_START + len(MDAT)
# Chunk offsets pointing at distinct positions inside mdat's payload.
CHUNK_OFFSETS = [MDAT_START + 8, MDAT_START + 8 + 1000, MDAT_START + 8 + 2000]
# A leaf box whose payload contains the literal bytes "stco" — must NOT be
# rewritten (the walker only recurses into known container boxes).
DECOY = _box(b"udta", b"xxstcoxx" + b"\x00" * 8)
MOOV = _box(
    b"moov",
    _box(b"trak", _box(b"mdia", _box(b"minf", _box(b"stbl", _stco(CHUNK_OFFSETS)))))
    + DECOY,
)


@pytest.fixture
def moov_at_end_mp4(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(FTYP + MDAT + MOOV)
    return str(path)


@pytest.fixture
def faststart_mp4(tmp_path):
    path = tmp_path / "faststart.mp4"
    path.write_bytes(FTYP + MOOV + MDAT)
    return str(path)


def test_moov_at_end_layout_is_remux(moov_at_end_mp4):
    size = MDAT_END + len(MOOV)
    assert _mp4_head_layout(moov_at_end_mp4, size) == {
        "mode": "remux",
        "mdat_start": MDAT_START,
        "mdat_end": MDAT_END,
    }
    # The layout is determined from the prefix alone — a barely-downloaded
    # file (headers only) must classify identically.
    assert _mp4_head_layout(moov_at_end_mp4, MDAT_START + 16) == {
        "mode": "remux",
        "mdat_start": MDAT_START,
        "mdat_end": MDAT_END,
    }
    assert mp4_remux_layout(moov_at_end_mp4, size) == (MDAT_START, MDAT_END)
    assert not is_pipe_streamable(moov_at_end_mp4, size)


def test_undetermined_prefix_returns_none(moov_at_end_mp4):
    # Not enough contiguous bytes to see past ftyp's header.
    assert _mp4_head_layout(moov_at_end_mp4, 10) is None
    assert mp4_remux_layout(moov_at_end_mp4, 10) is None


def test_faststart_layout_is_direct(faststart_mp4):
    size = len(FTYP + MOOV + MDAT)
    assert _mp4_head_layout(faststart_mp4, size) == {"mode": "direct"}
    assert mp4_remux_layout(faststart_mp4, size) is None
    assert is_pipe_streamable(faststart_mp4, size)


def test_pipe_friendly_extension_needs_no_probe(tmp_path):
    assert is_pipe_streamable(str(tmp_path / "nonexistent.mkv"), 0)


def test_preamble_relocates_moov_and_shifts_chunk_offsets(moov_at_end_mp4):
    size = MDAT_END + len(MOOV)
    preamble = build_faststart_preamble(moov_at_end_mp4, MDAT_START, MDAT_END, size)
    assert preamble is not None
    # Preamble = original leading boxes + relocated moov, so the synthesized
    # stream (preamble + mdat) is exactly one moov longer up front.
    assert preamble[: len(FTYP)] == FTYP
    new_moov = preamble[len(FTYP):]
    assert len(new_moov) == len(MOOV)

    # Every stco offset must shift by len(moov) — mdat now sits that much later.
    idx = new_moov.find(b"stco")
    count = struct.unpack(">I", new_moov[idx + 8 : idx + 12])[0]
    got = [
        struct.unpack(">I", new_moov[idx + 12 + 4 * i : idx + 16 + 4 * i])[0]
        for i in range(count)
    ]
    assert got == [o + len(MOOV) for o in CHUNK_OFFSETS]

    # The decoy leaf containing "stco" bytes must be untouched.
    assert b"xxstcoxx" in new_moov

    # End-to-end: each shifted offset must resolve to byte-identical payload
    # in the synthesized faststart stream.
    original = FTYP + MDAT + MOOV
    stream = preamble + MDAT
    for orig, new in zip(CHUNK_OFFSETS, got, strict=True):
        assert original[orig : orig + 16] == stream[new : new + 16]


def test_preamble_rejects_moovless_tail(tmp_path):
    # mdat followed by only free-space padding — no moov to relocate.
    path = tmp_path / "broken.mp4"
    path.write_bytes(FTYP + MDAT + _box(b"free", b"\x00" * 32))
    size = MDAT_END + 40
    assert build_faststart_preamble(str(path), MDAT_START, MDAT_END, size) is None
