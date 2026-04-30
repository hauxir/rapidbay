import contextlib
import datetime
import math
import os
import re
import shlex
import subprocess
import tempfile
import threading
import time
import urllib.parse
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from typing import Any, Callable, Dict, List, Tuple

import log
import settings
from common import threaded
from pymediainfo import MediaInfo
from subtitles import get_subtitle_language


def _recursive_filepaths(dir_name: str) -> List[str]:
    list_of_file: List[str] = os.listdir(dir_name)
    all_files: List[str] = []
    for entry in list_of_file:
        full_path: str = os.path.join(dir_name, entry)
        if os.path.isdir(full_path):
            all_files = all_files + _recursive_filepaths(full_path)
        else:
            all_files.append(full_path)
    return all_files


def get_sub_tracks(filepath: str) -> List[Tuple[int, str]]:
    media_info: Any = MediaInfo.parse(filepath)
    return [
        (int(t.streamorder), t.language or "en")
        for t in [
            t for t in media_info.tracks if t.track_type == "Text" and "Picture" not in (t.codec_id_info or "")
        ]
        if t.streamorder
    ]


def _extract_subtitles_as_vtt(filepath: str, output_dir: str) -> Any:
    basename: str = os.path.basename(filepath)
    filename_without_extension: str = os.path.splitext(basename)[0]
    sub_tracks: List[Tuple[int, str]] = get_sub_tracks(filepath)
    args: List[str] = ["ffmpeg", "-nostdin", "-v", "quiet", "-i", filepath]
    for (i, lang) in sub_tracks:
        args += [
            "-map", f"0:{i}",
            os.path.join(output_dir, f"{filename_without_extension}.{i}_{lang}.vtt"),
        ]
    return Popen(args)


def _cleanup_pre_emitted_vtts(output_dir: str, output_filepath: str) -> None:
    """Drop the SRT→VTT files that _run_subtitle_download pre-emits to make
    subtitles available during HLS playback.

    Once MP4 conversion has baked external SRTs into the MP4 and
    _extract_subtitles_as_vtt has written indexed "{stem}.{idx}_{lang}.vtt"
    files, the pre-emitted "{stem}_{lang}.vtt" files are duplicates with the
    same language tag — the browser surfaces both <track> elements
    simultaneously and the user sees subs rendered twice. Only delete when
    the indexed extraction actually produced output, so a failed extraction
    doesn't leave the picker empty.
    """
    stem = os.path.splitext(os.path.basename(output_filepath))[0]
    indexed_re = re.compile(re.escape(stem) + r"\.\d+_.+\.vtt$")
    pre_emitted_re = re.compile(re.escape(stem) + r"_.+\.vtt$")
    try:
        files = os.listdir(output_dir)
    except OSError:
        return
    if not any(indexed_re.fullmatch(f) for f in files):
        return
    for f in files:
        if pre_emitted_re.fullmatch(f):
            with contextlib.suppress(OSError):
                os.remove(os.path.join(output_dir, f))


def _incomplete_path(output_filepath: str) -> str:
    output_extension: str = os.path.splitext(output_filepath)[1]
    return f"{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}"


def _convert_file_to_mp4(input_filepath: str, output_filepath: str, subtitle_filepaths: List[Tuple[str | None, str]] | None = None) -> Any:
    if subtitle_filepaths is None:
        subtitle_filepaths = []
    media_info: Any = MediaInfo.parse(input_filepath)
    audio_codecs: List[str] = [
        t.format.lower() for t in media_info.tracks if t.track_type == "Audio"
    ]
    video_codecs: List[str] = [
        t.format.lower() for t in media_info.tracks if t.track_type == "Video"
    ]
    needs_audio_conversion: bool = not any("aac" in c for c in audio_codecs)
    needs_video_conversion: bool = settings.CONVERT_VIDEO and not any(("avc" in c or "hevc" in c or "av1" in c) for c in video_codecs)
    is_hevc: bool = any(("hevc" in c) for c in video_codecs)
    has_picture_subs: bool = (
        len(
            [
                t
                for t in media_info.tracks
                if t.track_type == "Text"
                and "Picture" in (t.codec_id_info or "")
            ]
        )
        > 0
    )
    n_sub_tracks: int = (
        len([t for t in media_info.tracks if t.track_type == "Text"])
        if not has_picture_subs
        else 0
    )

    log_path = f"{output_filepath}{settings.LOG_POSTFIX}"
    if media_info.tracks:
        try:
            duration: Any = next(t.duration for t in media_info.tracks if t.duration)
            duration_int: int | None = int(round(float(duration) / 1000))
        except StopIteration:
            duration_int = None
        with open(log_path, "w") as f:
            f.write(f"{duration_int}\r")

    args: List[str] = ["ffmpeg", "-nostdin", "-threads", "0", "-i", input_filepath]
    for (_, fn) in subtitle_filepaths:
        args += ["-f", "srt", "-i", fn]
    args += ["-map", "0:v?", "-map", "0:a?"]
    if n_sub_tracks > 0:
        args += ["-map", "0:s?"]
    if needs_audio_conversion:
        args += ["-acodec", "aac", "-ab", settings.AAC_BITRATE, "-ac", str(settings.AAC_CHANNELS)]
    else:
        args += ["-acodec", "copy"]
    if needs_video_conversion:
        # VIDEO_CONVERSION_PARAMS is operator-supplied (not user-controlled);
        # split with shlex so multi-token params like "libx264 -preset ultrafast"
        # become separate argv entries.
        args += ["-vcodec", *shlex.split(settings.VIDEO_CONVERSION_PARAMS)]
    else:
        args += ["-vcodec", "copy"]
    for i in range(1, len(subtitle_filepaths) + 1):
        args += ["-map", f"{i}?"]
    for i, (lang, _) in enumerate(subtitle_filepaths):
        if lang is not None:
            args += [f"-metadata:s:s:{i + n_sub_tracks}", f"language={lang}"]
    args += ["-c:s", "mov_text", "-movflags", "faststart", "-v", "quiet", "-stats"]
    if is_hevc:
        args += ["-tag:v", "hvc1"]
    args.append(_incomplete_path(output_filepath))

    # Append ffmpeg's stderr to the same log file the duration was written to.
    # Popen dups the fd, so the parent can close immediately after spawn.
    with open(log_path, "a") as log_f:
        return Popen(args, stderr=log_f, stdout=DEVNULL)


def get_conversion_progress(filepath: str) -> float:
    log_filepath: str = f"{filepath}{settings.LOG_POSTFIX}"
    if os.path.isfile(log_filepath):
        with open(log_filepath) as f:
            lines: List[str] = f.readlines()
            first_line: str = lines[0]
            last_line: str = lines[-1]
            duration: int = int(first_line)
            current_duration_match = re.search(r"time=\s*(\d\d\:\d\d\:\d\d)\s*", last_line)
            if current_duration_match:
                current_duration_str: str = current_duration_match.group(1)
                current_duration_struct = time.strptime(
                    current_duration_str.split(",")[0], "%H:%M:%S"
                )
                current_duration_seconds: float = datetime.timedelta(
                    hours=current_duration_struct.tm_hour,
                    minutes=current_duration_struct.tm_min,
                    seconds=current_duration_struct.tm_sec,
                ).total_seconds()
                return current_duration_seconds / duration
    return 0.0


PIPE_READ_CHUNK = 256 * 1024  # 256KB chunks for pipe feeder

# Containers that support sequential reading from a pipe (no seeking needed)
PIPE_FRIENDLY_EXTENSIONS = {".mkv", ".avi", ".ts", ".mpg", ".mpeg"}


def _detect_video_codec(filepath: str) -> str:
    """Detect video codec from file. Returns 'hevc', 'h264', etc.

    Uses ffprobe as the primary detector — it parses MKV/Matroska partial
    files more reliably than MediaInfo, which can miss the codec when the
    Tracks element hasn't fully landed yet at the start-of-stream threshold.
    Falls back to MediaInfo, then to "h264" as a last resort.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_name",
                "-of", "default=nw=1:nk=1",
                filepath,
            ],
            capture_output=True, text=True, timeout=15, check=False,
        )
        codec = result.stdout.strip().lower()
        if codec:
            if "hevc" in codec or "h265" in codec:
                return "hevc"
            if "h264" in codec or "avc" in codec:
                return "h264"
            return codec
    except (TimeoutExpired, OSError):
        pass
    try:
        media_info: Any = MediaInfo.parse(filepath)
        for t in media_info.tracks:
            if t.track_type == "Video" and t.format:
                fmt = t.format.lower()
                if "hevc" in fmt or "h265" in fmt:
                    return "hevc"
                if "avc" in fmt or "h264" in fmt:
                    return "h264"
                return fmt
    except Exception:
        pass
    return "h264"


def _detect_audio_codec(filepath: str) -> str:
    """Detect audio codec from file. Returns 'aac', 'ac3', etc."""
    try:
        media_info: Any = MediaInfo.parse(filepath)
        for t in media_info.tracks:
            if t.track_type == "Audio" and t.format:
                return t.format.lower()
    except Exception:
        pass
    return ""


class VideoConverter:
    def __init__(self) -> None:
        self.file_conversions: Dict[str, bool] = {}

    @threaded
    @log.catch_and_log_exceptions
    def convert_file(self, input_filepath: str, output_filepath: str) -> None:
        try:

            if len(self.file_conversions.keys()) >= settings.MAX_PARALLEL_CONVERSIONS:
                return
            if self.file_conversions.get(output_filepath):
                return

            self.file_conversions[output_filepath] = True

            output_dir: str = os.path.dirname(output_filepath)
            os.makedirs(output_dir, exist_ok=True)

            # Gather subtitle files
            basename: str = os.path.basename(input_filepath)
            filename_without_extension: str = os.path.splitext(basename)[0]

            subtitle_filepaths: List[Tuple[str | None, str]] = [
                (get_subtitle_language(os.path.basename(filepath)), filepath)
                for filepath in _recursive_filepaths(os.path.dirname(input_filepath))
                if (os.path.basename(filepath).lower()).startswith(
                    filename_without_extension.lower()
                )
                and filepath.endswith(".srt")
            ]

            conversion: Any = _convert_file_to_mp4(
                input_filepath, output_filepath, subtitle_filepaths=subtitle_filepaths
            )
            conversion.wait()

            if conversion.returncode != 0:
                raise Exception(f"Conversion failed for {input_filepath}")

            # Atomic publish: ffmpeg wrote to the .incomplete path; rename now
            # that we know the encode succeeded. Replaces the previous shell
            # `&&` chain with mv.
            os.replace(_incomplete_path(output_filepath), output_filepath)

            _extract_subtitles_as_vtt(output_filepath, output_dir).wait()
            _cleanup_pre_emitted_vtts(output_dir, output_filepath)

        finally:
            with contextlib.suppress(KeyError):
                del self.file_conversions[output_filepath]


class HLSStreamer:
    def __init__(self) -> None:
        # Maps m3u8 path → live ffmpeg Popen, so streams can be terminated when
        # the underlying torrent goes away (orphan-prevention).
        self.active_streams: Dict[str, Popen[bytes]] = {}
        # Paths currently being deliberately stopped (torrent removed, etc).
        # Used to suppress the failure-marking branch in _run_stream so a
        # forced shutdown isn't recorded as an unrecoverable codec failure.
        self._stopping: set[str] = set()
        self._reservation_lock = threading.Lock()

    @staticmethod
    def _failed_marker(m3u8_path: str) -> str:
        return m3u8_path + ".failed"

    @classmethod
    def is_failed(cls, m3u8_path: str) -> bool:
        # Marker is on disk so the verdict survives daemon restarts — otherwise
        # a known-bad-codec file would re-prompt ▶ every time the daemon comes up.
        return os.path.isfile(cls._failed_marker(m3u8_path))

    @classmethod
    def mark_failed(cls, m3u8_path: str) -> None:
        with contextlib.suppress(OSError), open(cls._failed_marker(m3u8_path), "w"):
            pass

    @classmethod
    def clear_failed(cls, m3u8_path: str) -> None:
        with contextlib.suppress(OSError):
            os.remove(cls._failed_marker(m3u8_path))

    def stop(self, m3u8_path: str) -> None:
        with self._reservation_lock:
            if m3u8_path not in self.active_streams:
                return
            # Record the request even if the Popen hasn't been registered yet,
            # so the start path (below) can honor it as soon as proc is created.
            self._stopping.add(m3u8_path)
            proc = self.active_streams.get(m3u8_path)
        if proc:
            with contextlib.suppress(Exception):
                proc.terminate()

    def stop_under(self, output_dir: str) -> None:
        norm = os.path.normpath(output_dir) + os.sep
        with self._reservation_lock:
            paths = [p for p in self.active_streams if os.path.normpath(p).startswith(norm)]
        for p in paths:
            self.stop(p)

    def start_stream(
        self,
        input_filepath: str,
        output_dir: str,
        get_sequential_bytes: Callable[[], int],
        total_file_size: int,
        m3u8_filename: str = "stream.m3u8",
    ) -> bool:
        """Reserve a stream slot synchronously and kick off ffmpeg in a thread.

        Returns True if a stream is now active (newly started or already running),
        False if capacity is exhausted.
        """
        m3u8_path = os.path.join(output_dir, m3u8_filename)
        if self.is_failed(m3u8_path):
            return False
        with self._reservation_lock:
            # Use `in` (not truthiness) — placeholder reservations sit in the
            # dict as None between start_stream and Popen creation, and a
            # truthy check would let a duplicate caller re-enter that window.
            if m3u8_path in self.active_streams:
                return True
            if len(self.active_streams) >= settings.MAX_PARALLEL_HLS_STREAMS:
                return False
            # Placeholder reservation; replaced with real Popen inside _run_stream.
            self.active_streams[m3u8_path] = None  # type: ignore[assignment]
        self._run_stream(
            input_filepath,
            output_dir,
            get_sequential_bytes,
            total_file_size,
            m3u8_filename,
            m3u8_path,
        )
        return True

    @threaded
    @log.catch_and_log_exceptions
    def _run_stream(
        self,
        input_filepath: str,
        output_dir: str,
        get_sequential_bytes: Callable[[], int],
        total_file_size: int,
        m3u8_filename: str,
        m3u8_path: str,
    ) -> None:
        try:
            os.makedirs(output_dir, exist_ok=True)

            segment_prefix = os.path.splitext(m3u8_filename)[0]
            segment_pattern = os.path.join(output_dir, f"{segment_prefix}_seg_%04d.m4s")
            init_filename = f"{segment_prefix}_init.mp4"
            stderr_log_path = os.path.join(output_dir, m3u8_filename + ".log")

            # Detect video codec for proper tagging
            video_codec = _detect_video_codec(input_filepath)
            video_tag = "hvc1" if video_codec == "hevc" else "avc1"

            # Copy audio when source is already AAC; otherwise transcode. The
            # aac_adtstoasc bitstream filter is needed when feeding ADTS-AAC
            # (typical of .ts) into an fMP4 segment, but is harmless on
            # transcode output too.
            audio_codec = _detect_audio_codec(input_filepath)
            if "aac" in audio_codec:
                audio_args = ["-c:a", "copy", "-bsf:a", "aac_adtstoasc"]
            else:
                audio_args = [
                    "-acodec", "aac",
                    "-ab", settings.AAC_BITRATE,
                    "-ac", str(settings.AAC_CHANNELS),
                    "-bsf:a", "aac_adtstoasc",
                ]

            hls_time = str(settings.HLS_SEGMENT_DURATION)
            ffmpeg_cmd = [
                "ffmpeg", "-nostdin",
                "-i", "pipe:0",
                # ffmpeg's default per-output-type stream selection auto-maps
                # the input's subtitle track and emits WebVTT segments next to
                # the video segments (named "{stem}{N}.vtt"). We surface
                # subtitles separately via the master playlist, so disable
                # subtitle output here to keep the segment dir clean.
                "-sn",
                "-vcodec", "copy",
                *audio_args,
                "-tag:v", video_tag,
                "-hls_playlist_type", "event",
                "-f", "hls",
                "-hls_segment_type", "fmp4",
                "-hls_time", hls_time,
                "-hls_init_time", hls_time,
                "-hls_fmp4_init_filename", init_filename,
                "-hls_segment_filename", segment_pattern,
                m3u8_path,
            ]

            with open(stderr_log_path, "w") as stderr_log:
                proc = Popen(ffmpeg_cmd, stdin=PIPE, stdout=DEVNULL, stderr=stderr_log)
                # Register the live process and honor any stop request that
                # arrived before Popen was created (start_stream reserves the
                # slot synchronously, the Popen itself is created here).
                with self._reservation_lock:
                    self.active_streams[m3u8_path] = proc
                    pending_stop = m3u8_path in self._stopping
                if pending_stop:
                    with contextlib.suppress(Exception):
                        proc.terminate()
                feeder = threading.Thread(
                    target=self._pipe_feeder,
                    args=(input_filepath, proc, get_sequential_bytes, total_file_size, m3u8_path),
                )
                feeder.start()
                feeder.join()
                # Bounded wait: once the feeder closes stdin, ffmpeg should
                # flush and exit within seconds. If it hangs (broken stream,
                # internal deadlock) the slot would otherwise be held forever
                # — only stop_under from torrent removal could free it. Mark
                # intentional before terminating so a forced kill isn't
                # recorded as an unrecoverable codec failure.
                try:
                    proc.wait(timeout=30)
                except TimeoutExpired:
                    log.debug(f"HLS ffmpeg did not exit 30s after stdin close, terminating: {m3u8_path}")
                    with self._reservation_lock:
                        self._stopping.add(m3u8_path)
                    with contextlib.suppress(Exception):
                        proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except TimeoutExpired:
                        with contextlib.suppress(Exception):
                            proc.kill()
                        with contextlib.suppress(Exception):
                            proc.wait(timeout=5)

            if proc.returncode != 0:
                with self._reservation_lock:
                    intentional = m3u8_path in self._stopping
                if not intentional:
                    with open(stderr_log_path) as f:
                        stderr = f.read()
                    print(f"HLS conversion failed for {input_filepath}: exit code {proc.returncode}: {stderr[-500:]}")
                    # Persist a failure marker so the frontend stops surfacing
                    # the ▶ button — even across restarts.
                    self.mark_failed(m3u8_path)
                # Drop the partial m3u8 either way: an event playlist without
                # ENDLIST will hang players that try to play it later.
                with contextlib.suppress(OSError):
                    os.remove(m3u8_path)
                return

            # Finalize the m3u8: switch EVENT→VOD and append ENDLIST
            if os.path.isfile(m3u8_path):
                with open(m3u8_path) as f:
                    content = f.read()
                if "#EXT-X-ENDLIST" not in content:
                    content = content.replace("#EXT-X-PLAYLIST-TYPE:EVENT", "#EXT-X-PLAYLIST-TYPE:VOD")
                    content += "#EXT-X-ENDLIST\n"
                    with open(m3u8_path, "w") as f:
                        f.write(content)

            # Stream finished cleanly — drop the now-uninteresting stderr log.
            with contextlib.suppress(OSError):
                os.remove(stderr_log_path)

            # Extract embedded subtitles as VTT from the original file
            if os.path.isfile(input_filepath):
                with contextlib.suppress(Exception):
                    _extract_subtitles_as_vtt(input_filepath, output_dir).wait()

        finally:
            with self._reservation_lock:
                self.active_streams.pop(m3u8_path, None)
                self._stopping.discard(m3u8_path)

    def _pipe_feeder(
        self,
        filepath: str,
        proc: Popen,  # type: ignore[type-arg]
        get_sequential_bytes: Callable[[], int],
        total_file_size: int,
        m3u8_path: str,
    ) -> None:
        bytes_written = 0
        try:
            while not os.path.isfile(filepath):
                if proc.poll() is not None:
                    return
                time.sleep(0.5)

            # Initialize the stall clock only after the input file exists —
            # waiting for libtorrent to materialize the file isn't a stall.
            last_progress_time = time.monotonic()

            with open(filepath, "rb") as f:
                while True:
                    if proc.poll() is not None:
                        break

                    available = get_sequential_bytes()
                    # Cap by current on-disk size: the piece estimator can run
                    # ahead of bytes flushed to the file, and reading past EOF
                    # would otherwise spin in a tight retry loop.
                    with contextlib.suppress(OSError):
                        available = min(available, os.path.getsize(filepath))

                    if available <= bytes_written:
                        # Watchdog: if the torrent has been making no progress
                        # for HLS_STALL_TIMEOUT, free the slot. Routed through
                        # self.stop() so _run_stream's intentional-exit path
                        # handles cleanup (no .failed marker — torrent might
                        # recover later and the user can ▶ again).
                        if time.monotonic() - last_progress_time > settings.HLS_STALL_TIMEOUT:
                            log.debug(f"HLS stream stalled ({settings.HLS_STALL_TIMEOUT}s no progress): {m3u8_path}")
                            self.stop(m3u8_path)
                            return
                        time.sleep(0.5)
                        continue

                    to_read = available - bytes_written
                    hit_eof = False
                    while to_read > 0:
                        chunk_size = min(to_read, PIPE_READ_CHUNK)
                        data = f.read(chunk_size)
                        if not data:
                            hit_eof = True
                            break
                        try:
                            proc.stdin.write(data)  # type: ignore[union-attr]
                            proc.stdin.flush()  # type: ignore[union-attr]
                        except BrokenPipeError:
                            return
                        bytes_written += len(data)
                        to_read -= len(data)
                        last_progress_time = time.monotonic()

                    if hit_eof:
                        time.sleep(0.5)
                        continue

                    if bytes_written >= total_file_size and available >= total_file_size:
                        break

        finally:
            with contextlib.suppress(Exception):
                proc.stdin.close()  # type: ignore[union-attr]


def _atomic_write(path: str, content: str) -> None:
    # Use a unique tmp file so concurrent writers can't clobber each other's
    # in-flight tmp before the rename.
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        # mkstemp defaults to 0600; nginx workers run as www-data and need
        # read access to the playlist files served from /play/.
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


# Cache of master-playlist signatures so we don't rewrite identical content on
# every status poll (frontend polls every 1-3s per active viewer).
_master_playlist_cache: Dict[str, Tuple[str, ...]] = {}
_master_playlist_cache_lock = threading.Lock()


def clear_master_playlist_cache_under(output_dir: str) -> None:
    """Drop master-playlist cache entries rooted under `output_dir`.

    Called on torrent removal so the cache doesn't grow unbounded across the
    daemon's lifetime; entries are scoped to per-torrent output dirs that
    disappear when the torrent does.
    """
    norm = os.path.normpath(output_dir) + os.sep
    with _master_playlist_cache_lock:
        for key in [k for k in _master_playlist_cache if os.path.normpath(k).startswith(norm)]:
            _master_playlist_cache.pop(key, None)


def write_hls_master_playlist(
    output_dir: str,
    video_m3u8_filename: str,
    vtt_filenames: List[str],
) -> str:
    """Generate an HLS master playlist that wraps the video media playlist and
    one subtitle media playlist per VTT file, so hls.js (and native HLS clients)
    can manage subtitle selection through EXT-X-MEDIA:TYPE=SUBTITLES tracks.

    Returns the master playlist filename.
    """
    base = os.path.splitext(video_m3u8_filename)[0]
    master_filename = f"{base}_master.m3u8"
    master_path = os.path.join(output_dir, master_filename)

    # Skip rewrite if the inputs are unchanged since last call. Frontend polls
    # the status endpoint every 1-3s; without this, the master + every subtitle
    # sub-playlist is rewritten on every poll for every viewer.
    signature: Tuple[str, ...] = (video_m3u8_filename, *vtt_filenames)
    with _master_playlist_cache_lock:
        if _master_playlist_cache.get(master_path) == signature and os.path.isfile(master_path):
            return master_filename

    # Use a generous fixed segment duration so hls.js never tries to fetch a
    # "next" subtitle segment; the VTT's own cue timestamps determine when each
    # cue is displayed, independent of EXTINF.
    duration = 86400.0
    target_duration = int(math.ceil(duration))

    # Compute language for each VTT, then assign unique NAMEs when a language
    # has multiple tracks. hls.js's subtitleTrackMatchesTextTrack matches by
    # label+lang, so two manifest tracks sharing both end up rendered
    # concurrently when one is selected.
    langs: List[str] = []
    for vtt in vtt_filenames:
        vtt_stem = os.path.splitext(vtt)[0]
        lang = vtt_stem.rsplit("_", 1)[-1] if "_" in vtt_stem else "und"
        langs.append(lang.replace('"', ""))
    lang_totals: Dict[str, int] = {}
    for lang in langs:
        lang_totals[lang] = lang_totals.get(lang, 0) + 1

    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    lang_seen: Dict[str, int] = {}
    for vtt, lang_safe in zip(vtt_filenames, langs, strict=False):
        lang_seen[lang_safe] = lang_seen.get(lang_safe, 0) + 1
        name = (
            f"{lang_safe.upper()} {lang_seen[lang_safe]}"
            if lang_totals[lang_safe] > 1
            else lang_safe.upper()
        )
        sub_playlist_filename = f"{vtt}.m3u8"
        sub_playlist_path = os.path.join(output_dir, sub_playlist_filename)
        # URI attributes in HLS manifests must be valid URIs — VTT filenames can
        # contain spaces, commas, and other chars that produce malformed manifests
        # if interpolated raw. Escape both the sub-playlist URI in the master and
        # the VTT URI inside the sub-playlist itself.
        sub_playlist_uri = urllib.parse.quote(sub_playlist_filename)
        vtt_uri = urllib.parse.quote(vtt)
        _atomic_write(
            sub_playlist_path,
            (
                "#EXTM3U\n"
                "#EXT-X-VERSION:3\n"
                "#EXT-X-PLAYLIST-TYPE:VOD\n"
                f"#EXT-X-TARGETDURATION:{target_duration}\n"
                "#EXT-X-MEDIA-SEQUENCE:0\n"
                f"#EXTINF:{duration:.3f},\n"
                f"{vtt_uri}\n"
                "#EXT-X-ENDLIST\n"
            ),
        )
        lines.append(
            f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{name}",'
            + f'LANGUAGE="{lang_safe}",DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,'
            + f'URI="{sub_playlist_uri}"'
        )

    bandwidth = 2000000
    if vtt_filenames:
        lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},SUBTITLES="subs"')
    else:
        lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth}")
    lines.append(urllib.parse.quote(video_m3u8_filename))

    _atomic_write(master_path, "\n".join(lines) + "\n")
    with _master_playlist_cache_lock:
        _master_playlist_cache[master_path] = signature
    return master_filename
