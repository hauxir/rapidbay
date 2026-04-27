import contextlib
import datetime
import math
import os
import re
import threading
import time
from subprocess import DEVNULL, PIPE, Popen
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
    return Popen(
        f'ffmpeg -nostdin -v quiet -i "{filepath}" '
        + " ".join(
            [
                f'-map 0:{i} "{output_dir}/{filename_without_extension}.{i}_{lang}.vtt"'
                for (i, lang) in sub_tracks
            ]
        ),
        shell=True,
    )


def _convert_file_to_mp4(input_filepath: str, output_filepath: str, subtitle_filepaths: List[Tuple[str | None, str]] | None = None) -> Any:
    if subtitle_filepaths is None:
        subtitle_filepaths = []
    output_extension: str = os.path.splitext(output_filepath)[1]
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

    if media_info.tracks:
        try:
            duration: Any = next(t.duration for t in media_info.tracks if t.duration)
            duration_int: int | None = int(round(float(duration) / 1000))
        except StopIteration:
            duration_int = None
        with open(f"{output_filepath}{settings.LOG_POSTFIX}", "w") as f:
            f.write(f"{duration_int}\r")
    return Popen(
        " ".join(
            [
                "ffmpeg -nostdin -threads 0",
                f'-i "{input_filepath}"',
                " ".join([f'-f srt -i "{fn}"' for (_, fn) in subtitle_filepaths]),
                "-map 0:v?",
                "-map 0:a?",
                "-map 0:s?" if n_sub_tracks > 0 else "",
                f"-acodec aac -ab {settings.AAC_BITRATE} -ac {settings.AAC_CHANNELS}"
                if needs_audio_conversion
                else "-acodec copy",
                "-vcodec " + settings.VIDEO_CONVERSION_PARAMS
                if needs_video_conversion
                else "-vcodec copy",
                " ".join([f"-map {i}?" for i in range(1, len(subtitle_filepaths) + 1)]),
                " ".join(
                    [
                        f"-metadata:s:s:{i + n_sub_tracks} language='{subtitle_filepaths[i][0]}'"
                        for i in range(0, len(subtitle_filepaths))
                        if subtitle_filepaths[i][0] is not None
                    ]
                ),
                "-c:s mov_text",
                "-movflags faststart",
                "-v quiet -stats",
                "-tag:v hvc1" if is_hevc else "",
                f'"{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}" 2>> "{output_filepath}{settings.LOG_POSTFIX}"',
                "&&",
                f'mv "{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}" "{output_filepath}"',
            ]
        ),
        shell=True,
    )


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
    """Detect video codec from file. Returns 'hevc', 'h264', etc."""
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

            _extract_subtitles_as_vtt(output_filepath, output_dir).wait()

        finally:
            with contextlib.suppress(KeyError):
                del self.file_conversions[output_filepath]


class HLSStreamer:
    def __init__(self) -> None:
        self.active_streams: Dict[str, bool] = {}
        self._reservation_lock = threading.Lock()

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
        with self._reservation_lock:
            if self.active_streams.get(m3u8_path):
                return True
            if len(self.active_streams) >= settings.MAX_PARALLEL_CONVERSIONS:
                return False
            self.active_streams[m3u8_path] = True
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

            hls_time = str(settings.HLS_SEGMENT_DURATION)
            ffmpeg_cmd = [
                "ffmpeg", "-nostdin",
                "-i", "pipe:0",
                "-vcodec", "copy",
                "-acodec", "aac", "-ab", settings.AAC_BITRATE,
                "-ac", str(settings.AAC_CHANNELS),
                "-bsf:a", "aac_adtstoasc",
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
                feeder = threading.Thread(
                    target=self._pipe_feeder,
                    args=(input_filepath, proc, get_sequential_bytes, total_file_size),
                )
                feeder.start()
                feeder.join()
                proc.wait()

            if proc.returncode != 0:
                with open(stderr_log_path) as f:
                    stderr = f.read()
                print(f"HLS conversion failed for {input_filepath}: exit code {proc.returncode}: {stderr[-500:]}")
                # Remove incomplete m3u8 so daemon retries the conversion
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

            # Extract embedded subtitles as VTT from the original file
            if os.path.isfile(input_filepath):
                with contextlib.suppress(Exception):
                    _extract_subtitles_as_vtt(input_filepath, output_dir).wait()

        finally:
            with contextlib.suppress(KeyError):
                del self.active_streams[m3u8_path]

    def _pipe_feeder(
        self,
        filepath: str,
        proc: Popen,  # type: ignore[type-arg]
        get_sequential_bytes: Callable[[], int],
        total_file_size: int,
    ) -> None:
        bytes_written = 0
        try:
            while not os.path.isfile(filepath):
                if proc.poll() is not None:
                    return
                time.sleep(0.5)

            with open(filepath, "rb") as f:
                while True:
                    if proc.poll() is not None:
                        break

                    available = get_sequential_bytes()
                    # Cap by current on-disk size: the piece estimator can run
                    # ahead of bytes flushed to the file, and reading past EOF
                    # would otherwise spin in a tight retry loop.
                    try:
                        available = min(available, os.path.getsize(filepath))
                    except OSError:
                        pass

                    if available <= bytes_written:
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

                    if hit_eof:
                        time.sleep(0.5)
                        continue

                    if bytes_written >= total_file_size and available >= total_file_size:
                        break

        finally:
            with contextlib.suppress(Exception):
                proc.stdin.close()  # type: ignore[union-attr]


def _atomic_write(path: str, content: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


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

    # Use a generous fixed segment duration so hls.js never tries to fetch a
    # "next" subtitle segment; the VTT's own cue timestamps determine when each
    # cue is displayed, independent of EXTINF.
    duration = 86400.0
    target_duration = int(math.ceil(duration))

    # Compute language for each VTT, then assign unique NAMEs when a language
    # has multiple tracks. hls.js's subtitleTrackMatchesTextTrack matches by
    # label+lang, so two manifest tracks sharing both end up rendered
    # concurrently when one is selected.
    langs = []
    for vtt in vtt_filenames:
        vtt_stem = os.path.splitext(vtt)[0]
        lang = vtt_stem.rsplit("_", 1)[-1] if "_" in vtt_stem else "und"
        langs.append(lang.replace('"', ""))
    lang_totals: Dict[str, int] = {}
    for lang in langs:
        lang_totals[lang] = lang_totals.get(lang, 0) + 1

    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    lang_seen: Dict[str, int] = {}
    for vtt, lang_safe in zip(vtt_filenames, langs):
        lang_seen[lang_safe] = lang_seen.get(lang_safe, 0) + 1
        if lang_totals[lang_safe] > 1:
            name = f"{lang_safe.upper()} {lang_seen[lang_safe]}"
        else:
            name = lang_safe.upper()
        sub_playlist_filename = f"{vtt}.m3u8"
        sub_playlist_path = os.path.join(output_dir, sub_playlist_filename)
        _atomic_write(
            sub_playlist_path,
            (
                "#EXTM3U\n"
                "#EXT-X-VERSION:3\n"
                "#EXT-X-PLAYLIST-TYPE:VOD\n"
                f"#EXT-X-TARGETDURATION:{target_duration}\n"
                "#EXT-X-MEDIA-SEQUENCE:0\n"
                f"#EXTINF:{duration:.3f},\n"
                f"{vtt}\n"
                "#EXT-X-ENDLIST\n"
            ),
        )
        lines.append(
            f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",'
            f'NAME="{name}",LANGUAGE="{lang_safe}",'
            f'DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,'
            f'URI="{sub_playlist_filename}"'
        )

    bandwidth = 2000000
    if vtt_filenames:
        lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},SUBTITLES="subs"')
    else:
        lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth}")
    lines.append(video_m3u8_filename)

    _atomic_write(master_path, "\n".join(lines) + "\n")
    return master_filename
