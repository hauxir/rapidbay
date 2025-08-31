import contextlib
import datetime
import os
import re
import time
from subprocess import Popen
from typing import Any, Dict, List, Optional, Tuple

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


def _extract_subtitles_as_vtt(filepath: str) -> Popen[bytes]:
    output_dir: str = os.path.dirname(filepath)
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


def _convert_file_to_mp4(input_filepath: str, output_filepath: str, subtitle_filepaths: Optional[List[Tuple[Optional[str], str]]] = None) -> Popen[bytes]:
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
            duration_int: Optional[int] = int(round(duration / 1000))
        except StopIteration:
            duration_int = None
        with open(f"{output_filepath}{settings.LOG_POSTFIX}", "w") as f:
            f.write(f"{duration_int}\r")
    return Popen(
        " ".join(
            [
                "ffmpeg -nostdin",
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


class VideoConverter:
    file_conversions: Dict[str, bool] = {}

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

            subtitle_filepaths: List[Tuple[Optional[str], str]] = [
                (get_subtitle_language(os.path.basename(filepath)), filepath)
                for filepath in _recursive_filepaths(os.path.dirname(input_filepath))
                if (os.path.basename(filepath).lower()).startswith(
                    filename_without_extension.lower()
                )
                and filepath.endswith(".srt")
            ]

            conversion: Popen[bytes] = _convert_file_to_mp4(
                input_filepath, output_filepath, subtitle_filepaths=subtitle_filepaths
            )
            conversion.wait()

            if conversion.returncode != 0:
                raise Exception(f"Conversion failed for {input_filepath}")

            _extract_subtitles_as_vtt(output_filepath).wait()

        finally:
            with contextlib.suppress(KeyError):
                del self.file_conversions[output_filepath]
