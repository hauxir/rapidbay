"""Video keyframe times from a container's index, without reading the media.

Seekable HLS cuts its playlist on keyframes so each segment starts with one, no
matter which ffmpeg job produced it. Both supported containers carry an index:
Matroska's Cues (one CuePoint per video keyframe, as mkvmerge and ffmpeg write
them) and MP4's sample tables (stss marks the sync samples; stts/ctts/elst give
their presentation times). Only the header and the index are read, through a
`read(offset, length)` callback that fetches byte ranges of the file.
"""

import struct
from typing import Callable, Dict, List, Tuple

Read = Callable[[int, int], bytes]

_MAX_INDEX_BYTES = 64 * 1024 * 1024
_HEAD_BYTES = 256 * 1024

# --- Matroska -------------------------------------------------------------

_EBML = 0x1A45DFA3
_SEGMENT = 0x18538067
_SEEKHEAD = 0x114D9B74
_SEEK = 0x4DBB
_SEEK_ID = 0x53AB
_SEEK_POSITION = 0x53AC
_INFO = 0x1549A966
_TIMESTAMP_SCALE = 0x2AD7B1
_TRACKS = 0x1654AE6B
_TRACK_ENTRY = 0xAE
_TRACK_NUMBER = 0xD7
_TRACK_TYPE = 0x83
_CUES = 0x1C53BB6B
_CUE_POINT = 0xBB
_CUE_TIME = 0xB3
_CUE_TRACK_POSITIONS = 0xB7
_CUE_TRACK = 0xF7
_CLUSTER = 0x1F43B675


def _vint(buf: bytes, pos: int, keep_marker: bool) -> Tuple[int, int] | None:
    """EBML variable-length integer at `pos`: (value, length). Element IDs
    keep their length-marker bit; sizes drop it. An all-ones size (unknown
    length) comes back as -1."""
    if pos >= len(buf):
        return None
    first = buf[pos]
    length = 1
    mask = 0x80
    while length <= 8 and not first & mask:
        mask >>= 1
        length += 1
    if length > 8 or pos + length > len(buf):
        return None
    value = first if keep_marker else first & (mask - 1)
    for b in buf[pos + 1:pos + length]:
        value = (value << 8) | b
    if not keep_marker and value == (1 << (7 * length)) - 1:
        return -1, length
    return value, length


def _element(buf: bytes, pos: int) -> Tuple[int, int, int] | None:
    """(id, data start, data size) of the element at `pos`; size -1 when
    unknown."""
    eid = _vint(buf, pos, keep_marker=True)
    if eid is None:
        return None
    size = _vint(buf, pos + eid[1], keep_marker=False)
    if size is None:
        return None
    return eid[0], pos + eid[1] + size[1], size[0]


def _children(buf: bytes, start: int, end: int) -> List[Tuple[int, int, int]]:
    out: List[Tuple[int, int, int]] = []
    pos = start
    while pos < end:
        el = _element(buf, pos)
        if el is None or el[2] < 0:
            break
        out.append(el)
        pos = el[1] + el[2]
    return out


def _uint(buf: bytes, start: int, size: int) -> int:
    return int.from_bytes(buf[start:start + size], "big")


def _read_element(read: Read, offset: int) -> Tuple[int, bytes] | None:
    """(id, payload) of the element at file offset `offset`."""
    head = read(offset, 16)
    el = _element(head, 0)
    if el is None or el[2] < 0 or el[2] > _MAX_INDEX_BYTES:
        return None
    payload = read(offset + el[1], el[2])
    if len(payload) != el[2]:
        return None
    return el[0], payload


def mkv_keyframes(read: Read) -> List[float] | None:
    """Sorted presentation times (seconds) of the video keyframes in the
    file's Cues, or None when the file has no usable Cues."""
    head = read(0, _HEAD_BYTES)
    ebml = _element(head, 0)
    if ebml is None or ebml[0] != _EBML:
        return None
    segment = _element(head, ebml[1] + ebml[2])
    if segment is None or segment[0] != _SEGMENT:
        return None
    seg_start = segment[1]

    top: Dict[int, bytes] = {}
    positions: Dict[int, int] = {}
    pos = seg_start
    while True:
        el = _element(head, pos)
        if el is None or el[0] == _CLUSTER or el[2] < 0:
            break
        if el[1] + el[2] > len(head):
            positions.setdefault(el[0], pos - seg_start)
            break
        top[el[0]] = head[el[1]:el[1] + el[2]]
        if el[0] == _SEEKHEAD:
            for sid, s_start, s_size in _children(head, el[1], el[1] + el[2]):
                if sid != _SEEK:
                    continue
                target_id = target_pos = None
                for cid, c_start, c_size in _children(head, s_start, s_start + s_size):
                    if cid == _SEEK_ID:
                        target_id = _uint(head, c_start, c_size)
                    elif cid == _SEEK_POSITION:
                        target_pos = _uint(head, c_start, c_size)
                if target_id is not None and target_pos is not None:
                    positions.setdefault(target_id, target_pos)
        pos = el[1] + el[2]

    for eid in (_INFO, _TRACKS, _CUES):
        if eid not in top and eid in positions:
            got = _read_element(read, seg_start + positions[eid])
            if got is not None and got[0] == eid:
                top[eid] = got[1]
    if _TRACKS not in top or _CUES not in top:
        return None

    scale = 1_000_000
    info = top.get(_INFO, b"")
    for cid, c_start, c_size in _children(info, 0, len(info)):
        if cid == _TIMESTAMP_SCALE:
            scale = _uint(info, c_start, c_size) or scale

    video_track = None
    tracks = top[_TRACKS]
    for tid, t_start, t_size in _children(tracks, 0, len(tracks)):
        if tid != _TRACK_ENTRY:
            continue
        number = kind = None
        for cid, c_start, c_size in _children(tracks, t_start, t_start + t_size):
            if cid == _TRACK_NUMBER:
                number = _uint(tracks, c_start, c_size)
            elif cid == _TRACK_TYPE:
                kind = _uint(tracks, c_start, c_size)
        if kind == 1 and number is not None:
            video_track = number
            break
    if video_track is None:
        return None

    cues = top[_CUES]
    times: List[float] = []
    for pid, p_start, p_size in _children(cues, 0, len(cues)):
        if pid != _CUE_POINT:
            continue
        cue_time = None
        is_video = False
        for cid, c_start, c_size in _children(cues, p_start, p_start + p_size):
            if cid == _CUE_TIME:
                cue_time = _uint(cues, c_start, c_size)
            elif cid == _CUE_TRACK_POSITIONS:
                for gid, g_start, g_size in _children(cues, c_start, c_start + c_size):
                    if gid == _CUE_TRACK and _uint(cues, g_start, g_size) == video_track:
                        is_video = True
        if cue_time is not None and is_video:
            times.append(cue_time * scale / 1e9)
    return sorted(set(times)) or None


# --- MP4 ------------------------------------------------------------------

_MP4_CONTAINERS = frozenset({b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts"})


def _boxes(buf: bytes, start: int, end: int) -> List[Tuple[bytes, int, int]]:
    """(type, payload start, payload end) for the boxes in buf[start:end]."""
    out: List[Tuple[bytes, int, int]] = []
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack(">I4s", buf[pos:pos + 8])
        header = 8
        if size == 1:
            if pos + 16 > end:
                break
            size = struct.unpack(">Q", buf[pos + 8:pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header or pos + size > end:
            break
        out.append((kind, pos + header, pos + size))
        pos += size
    return out


def _find(buf: bytes, start: int, end: int, path: List[bytes]) -> List[Tuple[int, int]]:
    """Payload spans of every box matching the type path below buf[start:end]."""
    matches: List[Tuple[int, int]] = []
    for kind, s, e in _boxes(buf, start, end):
        if kind != path[0]:
            continue
        if len(path) == 1:
            matches.append((s, e))
        elif kind in _MP4_CONTAINERS:
            matches.extend(_find(buf, s, e, path[1:]))
    return matches


def _find_moov(read: Read, size: int) -> bytes | None:
    pos = 0
    while pos + 8 <= size:
        head = read(pos, 16)
        if len(head) < 8:
            return None
        box_size, kind = struct.unpack(">I4s", head[:8])
        header = 8
        if box_size == 1:
            box_size = struct.unpack(">Q", head[8:16])[0]
            header = 16
        elif box_size == 0:
            box_size = size - pos
        if box_size < header:
            return None
        if kind == b"moov":
            if box_size > _MAX_INDEX_BYTES:
                return None
            data = read(pos, box_size)
            return data if len(data) == box_size else None
        pos += box_size
    return None


def mp4_keyframes(read: Read, size: int) -> List[float] | None:
    moov = _find_moov(read, size)
    if moov is None:
        return None
    mvhd = _find(moov, 0, len(moov), [b"moov", b"mvhd"])
    if not mvhd:
        return None
    s = mvhd[0][0]
    movie_timescale = struct.unpack(">I", moov[s + 20:s + 24] if moov[s] == 1 else moov[s + 12:s + 16])[0]
    for trak_s, trak_e in _find(moov, 0, len(moov), [b"moov", b"trak"]):
        hdlr = _find(moov, trak_s, trak_e, [b"mdia", b"hdlr"])
        if not hdlr or moov[hdlr[0][0] + 8:hdlr[0][0] + 12] != b"vide":
            continue
        mdhd = _find(moov, trak_s, trak_e, [b"mdia", b"mdhd"])
        stts = _find(moov, trak_s, trak_e, [b"mdia", b"minf", b"stbl", b"stts"])
        if not mdhd or not stts:
            return None
        m = mdhd[0][0]
        timescale = struct.unpack(">I", moov[m + 20:m + 24] if moov[m] == 1 else moov[m + 12:m + 16])[0]
        if not timescale or not movie_timescale:
            return None
        stss = _find(moov, trak_s, trak_e, [b"mdia", b"minf", b"stbl", b"stss"])
        ctts = _find(moov, trak_s, trak_e, [b"mdia", b"minf", b"stbl", b"ctts"])
        elst = _find(moov, trak_s, trak_e, [b"edts", b"elst"])
        return _mp4_track_keyframes(moov, timescale, movie_timescale, stts[0], stss, ctts, elst)
    return None


def _mp4_track_keyframes(
    moov: bytes,
    timescale: int,
    movie_timescale: int,
    stts: Tuple[int, int],
    stss: List[Tuple[int, int]],
    ctts: List[Tuple[int, int]],
    elst: List[Tuple[int, int]],
) -> List[float] | None:
    s = stts[0]
    (count,) = struct.unpack(">I", moov[s + 4:s + 8])
    dts: List[int] = []
    t = 0
    for i in range(count):
        n, delta = struct.unpack(">II", moov[s + 8 + i * 8:s + 16 + i * 8])
        for _ in range(n):
            dts.append(t)
            t += delta
    if not dts:
        return None

    offsets = [0] * len(dts)
    if ctts:
        c = ctts[0][0]
        signed = moov[c] == 1
        (count,) = struct.unpack(">I", moov[c + 4:c + 8])
        k = 0
        for i in range(count):
            n, off = struct.unpack(">Ii" if signed else ">II", moov[c + 8 + i * 8:c + 16 + i * 8])
            for _ in range(n):
                if k < len(offsets):
                    offsets[k] = off
                k += 1

    # Edit list: leading empty edits delay presentation; the first real edit's
    # media_time is where presentation starts in the track's timeline.
    empty = 0.0
    media_start = 0
    if elst:
        e = elst[0][0]
        version = moov[e]
        (count,) = struct.unpack(">I", moov[e + 4:e + 8])
        pos = e + 8
        for _ in range(count):
            if version == 1:
                duration, media_time = struct.unpack(">Qq", moov[pos:pos + 16])
                pos += 20
            else:
                duration, media_time = struct.unpack(">Ii", moov[pos:pos + 8])
                pos += 12
            if media_time == -1:
                empty += duration / movie_timescale
                continue
            media_start = media_time
            break

    if stss:
        st = stss[0][0]
        (count,) = struct.unpack(">I", moov[st + 4:st + 8])
        sync = [struct.unpack(">I", moov[st + 8 + i * 4:st + 12 + i * 4])[0] - 1 for i in range(count)]
    else:
        sync = list(range(len(dts)))
    times = sorted({(dts[i] + offsets[i] - media_start) / timescale + empty for i in sync if 0 <= i < len(dts)})
    return times or None
