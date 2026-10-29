"""Seekable HLS for files that are still downloading.

The pipe-fed HLSStreamer can only produce segments in order from the start of
the file, as an EVENT playlist that grows as data arrives, so a viewer can't
skip past what has been converted. This streamer instead:

1. Reads the file's duration, codecs and keyframe index (MKV Cues / MP4 sample
   tables) through the loopback TorrentFileServer, which downloads just the
   header and index.
2. Writes a complete VOD playlist up front, cut on keyframes, so every player
   (hls.js, Safari/iOS native HLS, Chromecast, AirPlay) shows the full seek bar
   at once.
3. Produces segments on demand with an ffmpeg job reading through the loopback
   server. A request for a segment the running job will reach soon waits for
   it; a request further away (a seek) restarts the job there with `-ss`, and
   the loopback server rushes the pieces at the new position.

Video is stream-copied, so ffmpeg can only cut on keyframes, and its HLS muxer
lays segments out relative to wherever a job started. Jobs therefore write one
piece per keyframe interval (`-hls_time` below any GOP length) and this module
groups the pieces into the playlist's segments itself. ffmpeg also restarts
each job's fragment decode times (`tfdt`) near zero, recording the real start
only in the job's init segment's edit list, which players ignore. So every
piece's `tfdt` is shifted back onto the source timeline (see fmp4.py) and one
canonical init segment, without edit lists, is served for all jobs.
"""

import bisect
import contextlib
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from subprocess import DEVNULL, Popen, TimeoutExpired
from typing import Any, Callable, Dict, List, Set

import fmp4
import keyframes
import log
import settings
from common import threaded
from video_conversion import HLSStreamer, atomic_write, extract_subtitles_as_vtt

# A request this many segments past the running job's frontier waits for the
# job instead of restarting it; further than that is treated as a seek.
_SEEK_GAP_SEGMENTS = 3
_SUPERVISE_INTERVAL = 0.25
# Added to every output timestamp so no job's first decode time is negative —
# ffmpeg would otherwise shift that job's timeline, and only that job's.
_TS_OFFSET = 10
# How far a piece's first decode time may sit from a keyframe boundary and
# still count as starting there: covers the B-frame decode/presentation gap
# and index rounding.
_BOUNDARY_TOLERANCE = 0.5
# `-ss` aims this far past a boundary keyframe. ffmpeg seeks to the keyframe
# at or before the target, but for Matroska with B-frames it first subtracts
# 3/23 s from the target, which would otherwise land a whole GOP early.
_SEEK_PAST_KEYFRAME = 0.25

SEEKABLE_EXTENSIONS = {".mkv", ".mp4"}

_SEGMENT_RE = re.compile(r"^(?P<stem>.+)_vod_(?P<n>\d+)\.m4s$")
_INIT_RE = re.compile(r"^(?P<stem>.+)_vod_init\.mp4$")


def segment_name(stem: str, n: int) -> str:
    return f"{stem}_vod_{n}.m4s"


def init_name(stem: str) -> str:
    return f"{stem}_vod_init.mp4"


def _probe_cache_name(stem: str) -> str:
    return f"{stem}_vod_probe.json"


def parse_segment_request(name: str) -> tuple[str, int | None] | None:
    """(stem, segment index) for a segment file name, (stem, None) for the
    init segment, None for anything else."""
    m = _SEGMENT_RE.match(name)
    if m:
        return m.group("stem"), int(m.group("n"))
    m = _INIT_RE.match(name)
    if m:
        return m.group("stem"), None
    return None


@dataclass
class Probe:
    start_time: float
    end_time: float
    video_codec: str
    audio_codec: str
    # Presentation times of each playlist segment's first keyframe.
    boundaries: List[float] = field(default_factory=list)


class ProbeUnavailableError(Exception):
    """Probing failed for a reason that may pass (the torrent was re-added,
    ffprobe timed out on a stalled swarm), so the file isn't marked failed."""


def probe_streams(url: str, timeout: float) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_entries", "format=duration,start_time:stream=codec_type,codec_name",
                url,
            ],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        info = json.loads(result.stdout or "{}")
    except (TimeoutExpired, OSError, ValueError) as e:
        raise ProbeUnavailableError(f"ffprobe failed: {e}") from e
    if result.returncode != 0:
        raise ProbeUnavailableError(f"ffprobe exited {result.returncode}: {result.stderr.strip()[-200:]}")
    return info


def _read_range(url: str, file_size: int, offset: int, length: int) -> bytes:
    if length <= 0 or offset >= file_size:
        return b""
    end = min(offset + length, file_size) - 1
    req = urllib.request.Request(url, headers={"Range": f"bytes={offset}-{end}"})
    with urllib.request.urlopen(req, timeout=settings.HLS_STALL_TIMEOUT) as resp:
        return resp.read()


def probe_file(filename: str, url: str, file_size: int, m3u8_path: str) -> Probe | None:
    """Duration, codecs and keyframe-aligned segment boundaries of a file,
    read through the loopback server. None when the file can't be streamed;
    None with the unseekable marker written when it has no keyframe index.
    Raises ProbeUnavailableError when it couldn't be read for now."""
    info = probe_streams(url, settings.HLS_STALL_TIMEOUT)
    streams: List[Dict[str, Any]] = info.get("streams", [])
    video = next((s.get("codec_name", "") for s in streams if s.get("codec_type") == "video"), "")
    audio = next((s.get("codec_name", "") for s in streams if s.get("codec_type") == "audio"), "")
    fmt: Dict[str, Any] = info.get("format", {})
    try:
        start_time = float(fmt.get("start_time") or 0)
        duration = float(fmt.get("duration") or 0)
    except (TypeError, ValueError):
        return None
    if not video or duration <= 0:
        return None

    def read(offset: int, length: int) -> bytes:
        return _read_range(url, file_size, offset, length)

    ext = os.path.splitext(filename)[1].lower()
    try:
        kf = keyframes.mkv_keyframes(read) if ext == ".mkv" else keyframes.mp4_keyframes(read, file_size)
    except OSError as e:
        raise ProbeUnavailableError(f"index unreadable: {e}") from e
    except (ValueError, IndexError) as e:
        log.debug(f"seekable HLS: keyframe index unreadable for {filename}: {e}")
        kf = None
    if not kf:
        with contextlib.suppress(OSError), open(SeekableHLSStreamer.unseekable_marker(m3u8_path), "w"):
            pass
        return None
    return Probe(
        start_time=start_time,
        end_time=start_time + duration,
        video_codec=video.lower(),
        audio_codec=audio.lower(),
        boundaries=segment_boundaries(kf, settings.HLS_SEGMENT_DURATION),
    )


# The first segments are kept short (where the GOPs allow): playback can't
# start until the whole first segment has downloaded.
_INITIAL_SEGMENTS = 3
_INITIAL_SEGMENT_DURATION = 2.0


def segment_boundaries(keyframe_times: List[float], segment_duration: float) -> List[float]:
    """Group keyframes into segments of at least `segment_duration` seconds
    (`_INITIAL_SEGMENT_DURATION` for the first few): each boundary is the
    first keyframe that far past the previous one."""
    boundaries: List[float] = []
    for t in keyframe_times:
        minimum = _INITIAL_SEGMENT_DURATION if len(boundaries) <= _INITIAL_SEGMENTS else segment_duration
        if not boundaries or t >= boundaries[-1] + minimum - 0.01:
            boundaries.append(t)
    return boundaries


def build_vod_playlist(stem: str, p: Probe) -> str:
    ends = p.boundaries[1:] + [max(p.end_time, p.boundaries[-1] + 0.001)]
    lengths = [max(end - start, 0.001) for start, end in zip(p.boundaries, ends, strict=True)]
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:7",
        f"#EXT-X-TARGETDURATION:{math.ceil(max(lengths))}",
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD",
        "#EXT-X-INDEPENDENT-SEGMENTS",
        f'#EXT-X-MAP:URI="{urllib.parse.quote(init_name(stem))}"',
    ]
    for i, length in enumerate(lengths):
        lines.append(f"#EXTINF:{length:.6f},")
        lines.append(urllib.parse.quote(segment_name(stem, i)))
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"


def ffmpeg_job_args(url: str, p: Probe, job_dir: str, start_segment: int) -> List[str]:
    args = ["ffmpeg", "-nostdin", "-v", "error"]
    if start_segment > 0:
        # Input seeking via the container index; -ss counts from the file's
        # start time.
        seek = p.boundaries[start_segment] - p.start_time + _SEEK_PAST_KEYFRAME
        # -noaccurate_seek: don't trim transcoded audio to the target, which
        # sits past the keyframe — that would leave an audio hole at the start
        # of the segment, and MSE stalls on holes.
        args += ["-ss", f"{max(seek, 0):.3f}", "-noaccurate_seek"]
    args += ["-copyts", "-i", url, "-sn", "-dn", "-c:v", "copy"]
    if "hevc" in p.video_codec or "h265" in p.video_codec:
        args += ["-tag:v", "hvc1"]
    elif "h264" in p.video_codec:
        args += ["-tag:v", "avc1"]
    if not p.audio_codec:
        args += ["-an"]
    elif "aac" in p.audio_codec:
        args += ["-c:a", "copy", "-bsf:a", "aac_adtstoasc"]
    else:
        args += ["-c:a", "aac", "-b:a", settings.AAC_BITRATE, "-ac", str(settings.AAC_CHANNELS)]
    args += [
        "-output_ts_offset", str(_TS_OFFSET),
        "-f", "hls",
        "-hls_segment_type", "fmp4",
        # Shorter than any GOP: one piece per keyframe interval.
        "-hls_time", "0.1",
        "-hls_list_size", "0",
        "-hls_playlist_type", "event",
        # Pieces and the playlist are written as .tmp and renamed when whole.
        "-hls_flags", "temp_file",
        "-hls_fmp4_init_filename", "init.mp4",
        "-hls_segment_filename", os.path.join(job_dir, "g_%d.m4s"),
        os.path.join(job_dir, "job.m3u8"),
    ]
    return args


class _Job:
    def __init__(self, proc: "Popen[bytes]", start: int, job_dir: str) -> None:
        self.proc = proc
        self.start = start
        self.job_dir = job_dir
        self.started_at = time.monotonic()
        self.stopping = False
        # Pieces of job.m3u8 already consumed.
        self.consumed = 0
        self.offsets: Dict[int, int] | None = None
        self.video_track: int | None = None
        self.video_timescale = 1
        # Segment being assembled from pieces, and whether it began exactly at
        # its boundary keyframe (pieces before the first boundary a job reaches
        # can't form a whole segment).
        self.building: int | None = None
        self.building_valid = False
        self.buffer = bytearray()
        # Segment index the job will finish next.
        self.frontier = start


class _Session:
    def __init__(
        self,
        magnet_hash: str,
        filename: str,
        output_dir: str,
        m3u8_path: str,
        url: str,
        file_size: int,
        input_filepath: str,
        is_abandoned: Callable[[], bool],
    ) -> None:
        self.magnet_hash = magnet_hash
        self.filename = filename
        self.output_dir = output_dir
        self.m3u8_path = m3u8_path
        self.stem = os.path.splitext(os.path.basename(m3u8_path))[0]
        self.url = url
        self.file_size = file_size
        self.input_filepath = input_filepath
        self.is_abandoned = is_abandoned
        self.probe: Probe | None = None
        self.job: _Job | None = None
        self.job_seq = 0
        # Counts segment requests; see wait_for.
        self.request_seq = 0
        self.cond = threading.Condition()
        self.stopped = False

    @property
    def n_segments(self) -> int:
        return len(self.probe.boundaries) if self.probe else 0

    def path(self, name: str) -> str:
        return os.path.join(self.output_dir, name)

    def segment_path(self, n: int) -> str:
        return self.path(segment_name(self.stem, n))

    def init_path(self) -> str:
        return self.path(init_name(self.stem))


class SeekableHLSStreamer:
    def __init__(
        self,
        on_probe: Callable[[str, str, Probe], None] | None = None,
        on_seek: Callable[[str], None] | None = None,
        on_unseekable: Callable[[str, str], object] | None = None,
    ) -> None:
        # m3u8 path → session. Same shape the daemon uses for HLSStreamer:
        # membership means a stream holds a slot.
        self.active_streams: Dict[str, _Session] = {}
        self._lock = threading.Lock()
        # m3u8 paths with a background probe running, and one lock per file so
        # a prefetch and a session never probe the same file twice.
        self._prefetching: Set[str] = set()
        self._probe_locks: Dict[str, threading.Lock] = {}
        # (magnet_hash, filename, probe) once the layout is known.
        self._on_probe = on_probe
        # magnet_hash whenever a job restarts mid-file.
        self._on_seek = on_seek
        # (magnet_hash, filename) when a file has no usable keyframe index; the
        # daemon falls back to the sequential streamer.
        self._on_unseekable = on_unseekable

    is_failed = HLSStreamer.is_failed
    mark_failed = HLSStreamer.mark_failed
    clear_failed = HLSStreamer.clear_failed

    @staticmethod
    def unseekable_marker(m3u8_path: str) -> str:
        return m3u8_path + ".noseek"

    def start_stream(
        self,
        magnet_hash: str,
        filename: str,
        output_dir: str,
        m3u8_filename: str,
        url: str,
        file_size: int,
        input_filepath: str,
        is_abandoned: Callable[[], bool],
    ) -> bool:
        m3u8_path = os.path.join(output_dir, m3u8_filename)
        if self.is_failed(m3u8_path):
            return False
        with self._lock:
            if m3u8_path in self.active_streams:
                return True
            if len(self.active_streams) >= settings.MAX_PARALLEL_HLS_STREAMS:
                return False
            session = _Session(
                magnet_hash, filename, output_dir, m3u8_path, url, file_size, input_filepath, is_abandoned
            )
            self.active_streams[m3u8_path] = session
        self._run_session(session)
        return True

    def stop(self, m3u8_path: str) -> None:
        with self._lock:
            session = self.active_streams.get(m3u8_path)
        if session is None:
            return
        with session.cond:
            session.stopped = True
            self._stop_job(session)
            session.cond.notify_all()

    def stop_under(self, output_dir: str) -> None:
        norm = os.path.normpath(output_dir) + os.sep
        with self._lock:
            paths = [p for p in self.active_streams if os.path.normpath(p).startswith(norm)]
        for p in paths:
            self.stop(p)

    def session_for(self, output_dir: str, stem: str) -> _Session | None:
        with self._lock:
            return self.active_streams.get(os.path.join(output_dir, stem + ".m3u8"))

    def wait_for(self, session: _Session, n: int | None, timeout: float) -> str | None:
        """Block until segment `n` (or the init segment when n is None) is on
        disk, starting or moving the ffmpeg job as needed. Returns its path, or
        None on timeout, when the session ends, or when a newer request moved
        the job somewhere that won't reach this segment.

        Only the newest segment request may move the job. A player that seeks
        abandons its pending requests, but their waiters live on here; if they
        could move the job too, they'd drag it back to the old position and
        the two would take turns restarting it."""
        deadline = time.monotonic() + timeout
        with session.cond:
            if n is not None:
                session.request_seq += 1
            my_request = session.request_seq
            while not session.stopped:
                if session.probe is not None:
                    if n is not None and not 0 <= n < session.n_segments:
                        return None
                    target = session.init_path() if n is None else session.segment_path(n)
                    if os.path.isfile(target):
                        return target
                    if n is None:
                        if session.job is None:
                            self._ensure_job(session, 0)
                    elif my_request == session.request_seq:
                        self._ensure_job(session, n)
                    elif session.job is None or not self._job_covers(session.job, n):
                        return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                session.cond.wait(min(remaining, 1.0))
        return None

    # --- internals -------------------------------------------------------

    @staticmethod
    def _load_probe(path: str) -> Probe | None:
        try:
            with open(path) as f:
                p = Probe(**json.load(f))
        except (OSError, ValueError, TypeError):
            return None
        return p if p.boundaries else None

    @threaded
    @log.catch_and_log_exceptions
    def _run_session(self, session: _Session) -> None:
        try:
            if not self._prepare(session):
                return
            self._supervise(session)
        finally:
            with session.cond:
                session.stopped = True
                self._stop_job(session)
                session.cond.notify_all()
            with self._lock:
                self.active_streams.pop(session.m3u8_path, None)

    def prefetch(self, filename: str, url: str, file_size: int, output_dir: str, m3u8_filename: str) -> None:
        """Probe a file in the background while its viewer is still on the
        download screen, so ▶ starts from a cached probe. Probing reads the
        header and then the index through the loopback server, so only the
        bytes it is blocked on are rushed, in the order it needs them —
        unlike rushing a fixed head and tail, which makes them all compete."""
        m3u8_path = os.path.join(output_dir, m3u8_filename)
        stem = os.path.splitext(m3u8_filename)[0]
        if (
            self.is_failed(m3u8_path)
            or os.path.isfile(self.unseekable_marker(m3u8_path))
            or os.path.isfile(os.path.join(output_dir, _probe_cache_name(stem)))
        ):
            return
        with self._lock:
            if m3u8_path in self._prefetching:
                return
            self._prefetching.add(m3u8_path)
        self._run_prefetch(filename, url, file_size, output_dir, m3u8_path)

    @threaded
    @log.catch_and_log_exceptions
    def _run_prefetch(self, filename: str, url: str, file_size: int, output_dir: str, m3u8_path: str) -> None:
        try:
            self._probe_cached(filename, url, file_size, output_dir, m3u8_path)
        except ProbeUnavailableError as e:
            log.debug(f"seekable HLS: prefetch of {filename} failed: {e}")
        finally:
            with self._lock:
                self._prefetching.discard(m3u8_path)

    def _probe_cached(self, filename: str, url: str, file_size: int, output_dir: str, m3u8_path: str) -> Probe | None:
        """The file's probe from the on-disk cache, probing (once, even when a
        prefetch and a session ask together) when there is none."""
        stem = os.path.splitext(os.path.basename(m3u8_path))[0]
        cache_path = os.path.join(output_dir, _probe_cache_name(stem))
        with self._lock:
            lock = self._probe_locks.setdefault(m3u8_path, threading.Lock())
        with lock:
            p = self._load_probe(cache_path)
            if p is not None:
                return p
            began = time.monotonic()
            p = probe_file(filename, url, file_size, m3u8_path)
            log.debug(f"seekable HLS: probed {filename} in {time.monotonic() - began:.1f}s")
            if p is not None:
                os.makedirs(output_dir, exist_ok=True)
                atomic_write(cache_path, json.dumps(asdict(p)))
            return p

    def _prepare(self, session: _Session) -> bool:
        try:
            p = self._probe_cached(
                session.filename, session.url, session.file_size, session.output_dir, session.m3u8_path
            )
        except ProbeUnavailableError as e:
            # No .failed marker: ▶ resurfaces and the viewer can retry.
            print(f"seekable HLS: couldn't probe {session.filename} yet: {e}")
            return False
        if session.stopped:
            return False
        if p is None:
            if os.path.isfile(self.unseekable_marker(session.m3u8_path)):
                print(f"seekable HLS: no keyframe index in {session.filename}, falling back to sequential HLS")
                if self._on_unseekable:
                    # Release this session's slot before the fallback
                    # claims one.
                    with self._lock:
                        self.active_streams.pop(session.m3u8_path, None)
                    self._on_unseekable(session.magnet_hash, session.filename)
            else:
                print(f"seekable HLS: {session.filename} has no streamable video")
                self.mark_failed(session.m3u8_path)
            return False
        if self._on_probe:
            self._on_probe(session.magnet_hash, session.filename, p)
        with session.cond:
            session.probe = p
            # Start producing from the beginning straight away; a resume or
            # seek request moves the job.
            if not os.path.isfile(session.segment_path(0)):
                self._ensure_job(session, 0)
        atomic_write(session.m3u8_path, build_vod_playlist(session.stem, p))
        return True

    def _supervise(self, session: _Session) -> None:
        last_complete_check = 0.0
        while True:
            time.sleep(_SUPERVISE_INTERVAL)
            if session.stopped:
                return
            if session.is_abandoned():
                log.debug(f"seekable HLS abandoned (no viewer for {settings.HLS_VIEWER_TIMEOUT}s): {session.m3u8_path}")
                self._discard_partial(session)
                return
            with session.cond:
                job = session.job
                job_ended = False
                if job is not None:
                    try:
                        progressed = self._drain(session, job)
                    except (OSError, ValueError) as e:
                        log.debug(f"seekable HLS: dropping job for {session.filename}: {e}")
                        self._stop_job(session)
                        progressed = False
                    if progressed:
                        session.cond.notify_all()
                    job_ended = session.job is job and job.proc.poll() is not None and not self._has_unconsumed(job)
                    if job_ended:
                        failed = (
                            job.proc.returncode != 0
                            and not job.stopping
                            and job.offsets is None
                            and time.monotonic() - job.started_at < settings.HLS_STALL_TIMEOUT
                        )
                        self._stop_job(session)
                        if failed:
                            print(f"seekable HLS: ffmpeg failed for {session.filename} (exit {job.proc.returncode})")
                            self.mark_failed(session.m3u8_path)
                            self._discard_partial(session)
                            return
                        session.cond.notify_all()
                # A job reaching EOF may have filled the last gap; otherwise
                # stat every segment file only every few seconds.
                now = time.monotonic()
                if job_ended or now - last_complete_check > 5:
                    last_complete_check = now
                    if self._complete(session):
                        break
        # Every segment exists: the playlist is a finished VOD that nginx
        # serves statically, so the session can release its slot.
        if os.path.isfile(session.input_filepath):
            with contextlib.suppress(Exception):
                extract_subtitles_as_vtt(session.input_filepath, session.output_dir).wait()

    @staticmethod
    def _job_pieces(job: _Job) -> tuple[List[tuple[str, float]], bool]:
        """(name, duration) of the job's finished pieces, and whether it has
        written its last one."""
        try:
            with open(os.path.join(job.job_dir, "job.m3u8")) as f:
                text = f.read()
        except OSError:
            return [], False
        pieces: List[tuple[str, float]] = []
        duration = 0.0
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#EXTINF:"):
                with contextlib.suppress(ValueError):
                    duration = float(line[len("#EXTINF:"):].split(",")[0])
            elif line and not line.startswith("#"):
                pieces.append((line, duration))
        return pieces, "#EXT-X-ENDLIST" in text

    def _has_unconsumed(self, job: _Job) -> bool:
        pieces, _ = self._job_pieces(job)
        return len(pieces) > job.consumed

    def _drain(self, session: _Session, job: _Job) -> bool:
        """Turn the job's finished pieces into playlist segments. Called with
        session.cond held. True when a segment was written."""
        p = session.probe
        assert p is not None
        pieces, ended = self._job_pieces(job)
        if len(pieces) <= job.consumed:
            return False
        if job.offsets is None:
            with open(os.path.join(job.job_dir, "init.mp4"), "rb") as f:
                init = f.read()
            job.offsets = fmp4.track_offsets(init)
            tracks = fmp4.timescales(init)
            job.video_track = next((tid for tid, (_, video) in tracks.items() if video), None)
            if job.video_track is None:
                raise ValueError("no video track in init segment")
            job.video_timescale = tracks[job.video_track][0]
            if not os.path.isfile(session.init_path()):
                _atomic_write_bytes(session.init_path(), fmp4.strip_edit_lists(init))
        wrote = False
        for name, duration in pieces[job.consumed:]:
            piece_path = os.path.join(job.job_dir, name)
            with open(piece_path, "rb") as f:
                raw = f.read()
            data, first = fmp4.rewrite_fragments(raw, job.offsets, keep_styp=False)
            job.consumed += 1
            with contextlib.suppress(OSError):
                os.remove(piece_path)
            if job.video_track not in first:
                job.buffer += data
                continue
            t = first[job.video_track] / job.video_timescale - _TS_OFFSET
            n = bisect.bisect_right(p.boundaries, t + _BOUNDARY_TOLERANCE) - 1
            if n != job.building:
                wrote |= self._finish_segment(session, job)
                job.building = n
                job.building_valid = n >= 0 and abs(t - p.boundaries[n]) < _BOUNDARY_TOLERANCE
                job.buffer = bytearray()
            job.buffer += data
            # Close the segment as soon as this piece reaches the next
            # boundary, rather than when the next segment's first piece shows
            # up: ffmpeg only writes a piece once it reads the following
            # keyframe, so waiting would cost a whole extra GOP of download.
            if n >= 0:
                segment_end = p.boundaries[n + 1] if n + 1 < len(p.boundaries) else p.end_time
                if t + duration >= segment_end - _BOUNDARY_TOLERANCE:
                    wrote |= self._finish_segment(session, job)
                    job.building = None
        if ended and job.consumed == len(pieces):
            # The job read to the end of the file, so the last segment is whole.
            wrote |= self._finish_segment(session, job)
            job.building = None
        return wrote

    def _finish_segment(self, session: _Session, job: _Job) -> bool:
        n = job.building
        if n is None or not job.building_valid or not job.buffer:
            return False
        job.frontier = max(job.frontier, n + 1)
        target = session.segment_path(n)
        if os.path.isfile(target):
            return False
        _atomic_write_bytes(target, bytes(job.buffer))
        return True

    def _complete(self, session: _Session) -> bool:
        return os.path.isfile(session.init_path()) and all(
            os.path.isfile(session.segment_path(i)) for i in range(session.n_segments)
        )

    @staticmethod
    def _job_covers(job: _Job, n: int) -> bool:
        """Whether the running job will reach segment `n` soon."""
        return job.proc.poll() is None and job.start <= n <= job.frontier + _SEEK_GAP_SEGMENTS

    def _ensure_job(self, session: _Session, n: int) -> None:
        """Called with session.cond held."""
        job = session.job
        if job is not None and self._job_covers(job, n):
            return
        p = session.probe
        if p is None or session.stopped:
            return
        self._stop_job(session)
        if self._on_seek and n != 0:
            self._on_seek(session.magnet_hash)
        session.job_seq += 1
        job_dir = session.path(f".{session.stem}_vod_job{session.job_seq}")
        shutil.rmtree(job_dir, ignore_errors=True)
        os.makedirs(job_dir)
        args = ffmpeg_job_args(session.url, p, job_dir, n)
        with open(os.path.join(job_dir, "ffmpeg.log"), "w") as log_f:
            proc = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=log_f)
        session.job = _Job(proc, n, job_dir)

    def _stop_job(self, session: _Session) -> None:
        job = session.job
        if job is None:
            return
        job.stopping = True
        if job.proc.poll() is None:
            # SIGKILL, not SIGTERM: a job is usually blocked reading the
            # download frontier, and ffmpeg only acts on SIGTERM once that read
            # returns. Its unfinished output is discarded anyway.
            with contextlib.suppress(Exception):
                job.proc.kill()
            with contextlib.suppress(TimeoutExpired):
                job.proc.wait(timeout=5)
        shutil.rmtree(job.job_dir, ignore_errors=True)
        session.job = None

    def _discard_partial(self, session: _Session) -> None:
        """Drop the playlist of an unfinished stream so the file's status
        offers ▶ again. Segments and the probe cache stay: a later session
        lays out the same segments, so they're reused."""
        with session.cond:
            session.stopped = True
            self._stop_job(session)
            session.cond.notify_all()
        if not self._complete(session):
            with contextlib.suppress(OSError):
                os.remove(session.m3u8_path)


def _atomic_write_bytes(path: str, data: bytes) -> None:
    tmp = f"{path}.{secrets.token_hex(4)}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)
