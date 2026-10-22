"""Fragmented-MP4 surgery for seekable HLS.

Every ffmpeg job writes fragments whose `tfdt` (decode time) restarts near zero
and records the job's real start in its init segment's edit list. Players
honour `tfdt`, not that edit list, so fragments from a job started mid-file
would be placed at the start of the timeline. These helpers read each job's
per-track start offset from its init segment, rewrite `tfdt` onto one shared
timeline, and produce a single canonical init segment without edit lists.
"""

import struct
from typing import Dict, List, Tuple


def _boxes(buf: bytes, start: int, end: int) -> List[Tuple[bytes, int, int, int]]:
    """(type, box start, payload start, box end) for the boxes in buf[start:end]."""
    out: List[Tuple[bytes, int, int, int]] = []
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack(">I4s", buf[pos:pos + 8])
        header = 8
        if size == 1:
            size = struct.unpack(">Q", buf[pos + 8:pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            raise ValueError(f"malformed box at {pos}")
        out.append((kind, pos, pos + header, pos + size))
        pos += size
    return out


def strip_edit_lists(init: bytes) -> bytes:
    """The init segment with every `edts` box removed."""
    def rebuild(start: int, end: int) -> bytes:
        out = b""
        for kind, box_start, payload, box_end in _boxes(init, start, end):
            if kind == b"edts":
                continue
            if kind in (b"moov", b"trak"):
                inner = rebuild(payload, box_end)
                out += struct.pack(">I", 8 + len(inner)) + kind + inner
            else:
                out += init[box_start:box_end]
        return out

    return rebuild(0, len(init))


def track_offsets(init: bytes) -> Dict[int, int]:
    """Per track id, the ticks (track timescale) to add to each fragment's
    `tfdt` to move it from the job's local timeline to the source's: the
    leading empty edit (where the job's first sample is presented) minus the
    edit's media time (that sample's composition offset)."""
    offsets: Dict[int, int] = {}
    movie_timescale = 1000
    for kind, _, payload, end in _boxes(init, 0, len(init)):
        if kind != b"moov":
            continue
        for k, _, p, _ in _boxes(init, payload, end):
            if k == b"mvhd":
                movie_timescale = struct.unpack(">I", init[p + 20:p + 24] if init[p] == 1 else init[p + 12:p + 16])[0]
        for k, _, p, e in _boxes(init, payload, end):
            if k != b"trak":
                continue
            track_id = timescale = None
            empty = 0
            media_time = 0
            for tk, _, tp, te in _boxes(init, p, e):
                if tk == b"tkhd":
                    track_id = struct.unpack(">I", init[tp + 20:tp + 24] if init[tp] == 1 else init[tp + 12:tp + 16])[0]
                elif tk == b"mdia":
                    for mk, _, mp, _ in _boxes(init, tp, te):
                        if mk == b"mdhd":
                            timescale = struct.unpack(
                                ">I", init[mp + 20:mp + 24] if init[mp] == 1 else init[mp + 12:mp + 16]
                            )[0]
                elif tk == b"edts":
                    for ek, _, ep, _ in _boxes(init, tp, te):
                        if ek != b"elst":
                            continue
                        version = init[ep]
                        (count,) = struct.unpack(">I", init[ep + 4:ep + 8])
                        pos = ep + 8
                        for _ in range(count):
                            if version == 1:
                                duration, mt = struct.unpack(">Qq", init[pos:pos + 16])
                                pos += 20
                            else:
                                duration, mt = struct.unpack(">Ii", init[pos:pos + 8])
                                pos += 12
                            if mt == -1:
                                empty += duration
                                continue
                            media_time = mt
                            break
            if track_id is not None and timescale:
                offsets[track_id] = round(empty * timescale / movie_timescale) - media_time
    return offsets


def rewrite_fragments(data: bytes, offsets: Dict[int, int], keep_styp: bool) -> Tuple[bytes, Dict[int, int]]:
    """Shift every `tfdt` in a media segment by its track's offset, dropping
    `sidx` boxes (their times would be stale) and, unless `keep_styp`, the
    leading `styp` so pieces can be concatenated into one segment.

    Returns the rewritten bytes and the first shifted decode time per track."""
    buf = bytearray(data)
    first: Dict[int, int] = {}
    out = bytearray()
    for kind, box_start, payload, box_end in _boxes(data, 0, len(data)):
        if kind == b"sidx" or (kind == b"styp" and not keep_styp):
            continue
        if kind == b"moof":
            for k, _, p, e in _boxes(data, payload, box_end):
                if k != b"traf":
                    continue
                track_id = None
                for tk, _, tp, _ in _boxes(data, p, e):
                    if tk == b"tfhd":
                        track_id = struct.unpack(">I", data[tp + 4:tp + 8])[0]
                    elif tk == b"tfdt" and track_id is not None:
                        shift = offsets.get(track_id, 0)
                        if data[tp] == 1:
                            value = struct.unpack(">Q", data[tp + 4:tp + 12])[0] + shift
                            struct.pack_into(">Q", buf, tp + 4, value)
                        else:
                            value = struct.unpack(">I", data[tp + 4:tp + 8])[0] + shift
                            if value >= 1 << 32:
                                raise ValueError("tfdt overflow")
                            struct.pack_into(">I", buf, tp + 4, value)
                        first.setdefault(track_id, value)
        out += buf[box_start:box_end]
    return bytes(out), first


def timescales(init: bytes) -> Dict[int, Tuple[int, bool]]:
    """Per track id: (timescale, is_video)."""
    result: Dict[int, Tuple[int, bool]] = {}
    for kind, _, payload, end in _boxes(init, 0, len(init)):
        if kind != b"moov":
            continue
        for k, _, p, e in _boxes(init, payload, end):
            if k != b"trak":
                continue
            track_id = timescale = None
            video = False
            for tk, _, tp, te in _boxes(init, p, e):
                if tk == b"tkhd":
                    track_id = struct.unpack(">I", init[tp + 20:tp + 24] if init[tp] == 1 else init[tp + 12:tp + 16])[0]
                elif tk == b"mdia":
                    for mk, _, mp, _ in _boxes(init, tp, te):
                        if mk == b"mdhd":
                            timescale = struct.unpack(
                                ">I", init[mp + 20:mp + 24] if init[mp] == 1 else init[mp + 12:mp + 16]
                            )[0]
                        elif mk == b"hdlr":
                            video = init[mp + 8:mp + 12] == b"vide"
            if track_id is not None and timescale:
                result[track_id] = (timescale, video)
    return result
