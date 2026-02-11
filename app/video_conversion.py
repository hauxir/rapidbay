import contextlib
import os
import threading
import time
from subprocess import DEVNULL, PIPE, Popen
from typing import Any, Callable, Dict, List, Tuple

import log
import settings
from common import threaded
from pymediainfo import MediaInfo


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


PIPE_READ_CHUNK = 256 * 1024  # 256KB chunks for pipe feeder

# Containers that support sequential reading from a pipe (no seeking needed)
PIPE_FRIENDLY_EXTENSIONS = {".mkv", ".avi", ".ts", ".mpg", ".mpeg"}


def _is_hevc(filepath: str) -> bool:
    try:
        media_info: Any = MediaInfo.parse(filepath)
        for t in media_info.tracks:
            if t.track_type == "Video" and t.format and t.format.upper() == "HEVC":
                return True
    except Exception:
        pass
    return False


class HLSStreamer:
    def __init__(self) -> None:
        self.active_streams: Dict[str, bool] = {}

    @threaded
    @log.catch_and_log_exceptions
    def start_stream(
        self,
        input_filepath: str,
        output_dir: str,
        get_sequential_bytes: Callable[[], int],
        total_file_size: int,
        m3u8_filename: str = "stream.m3u8",
    ) -> None:
        m3u8_path = os.path.join(output_dir, m3u8_filename)
        try:
            if len(self.active_streams) >= settings.MAX_PARALLEL_CONVERSIONS:
                return
            if self.active_streams.get(m3u8_path):
                return

            self.active_streams[m3u8_path] = True
            os.makedirs(output_dir, exist_ok=True)

            segment_prefix = os.path.splitext(m3u8_filename)[0]
            segment_pattern = os.path.join(output_dir, f"{segment_prefix}_seg_%04d.m4s")
            init_filename = f"{segment_prefix}_init.mp4"
            stderr_log_path = os.path.join(output_dir, m3u8_filename + ".log")

            ext = os.path.splitext(input_filepath)[1].lower()
            use_pipe = ext in PIPE_FRIENDLY_EXTENSIONS

            ffmpeg_input = ["pipe:0"] if use_pipe else [input_filepath]
            ffmpeg_cmd = [
                "ffmpeg", "-nostdin", "-threads", "0",
                "-i", *ffmpeg_input,
                "-map", "0:v?", "-map", "0:a?",
                "-c:v", "copy",
                "-acodec", "aac", "-ab", settings.AAC_BITRATE,
                "-ac", str(settings.AAC_CHANNELS),
                "-movflags", "+negative_cts_offsets+default_base_moof",
                "-f", "hls",
                "-hls_time", str(settings.HLS_SEGMENT_DURATION),
                "-hls_playlist_type", "event",
                "-hls_segment_type", "fmp4",
                "-hls_fmp4_init_filename", init_filename,
                "-hls_flags", "independent_segments",
                "-hls_segment_filename", segment_pattern,
                m3u8_path,
            ]

            with open(stderr_log_path, "w") as stderr_log:
                if use_pipe:
                    proc = Popen(ffmpeg_cmd, stdin=PIPE, stdout=DEVNULL, stderr=stderr_log)
                    feeder = threading.Thread(
                        target=self._pipe_feeder,
                        args=(input_filepath, proc, get_sequential_bytes, total_file_size),
                    )
                    feeder.start()
                    feeder.join()
                else:
                    # MP4/MOV need seeking — wait for full file, then use direct input
                    while get_sequential_bytes() < total_file_size:
                        time.sleep(1)
                    proc = Popen(ffmpeg_cmd, stdin=DEVNULL, stdout=DEVNULL, stderr=stderr_log)
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

                    if available <= bytes_written:
                        time.sleep(0.5)
                        continue

                    to_read = available - bytes_written
                    while to_read > 0:
                        chunk_size = min(to_read, PIPE_READ_CHUNK)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        try:
                            proc.stdin.write(data)  # type: ignore[union-attr]
                            proc.stdin.flush()  # type: ignore[union-attr]
                        except BrokenPipeError:
                            return
                        bytes_written += len(data)
                        to_read -= len(data)

                    if bytes_written >= total_file_size and available >= total_file_size:
                        break

        finally:
            with contextlib.suppress(Exception):
                proc.stdin.close()  # type: ignore[union-attr]
