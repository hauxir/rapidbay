import asyncio
import datetime
import os
import re
import time
from pathlib import Path
from subprocess import Popen

import log
import settings
from common import threaded
from pymediainfo import MediaInfo
from subtitles import get_subtitle_language
from threading import Lock


def _recursive_filepaths(dir_name):
    list_of_file = os.listdir(dir_name)
    all_files = list()
    for entry in list_of_file:
        full_path = os.path.join(dir_name, entry)
        if os.path.isdir(full_path):
            all_files = all_files + _recursive_filepaths(full_path)
        else:
            all_files.append(full_path)
    return all_files


def _extract_subtitles_as_vtt(filepath):
    output_dir = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    filename_without_extension = os.path.splitext(basename)[0]
    media_info = MediaInfo.parse(filepath)
    sub_tracks = [
        (int(t.streamorder), t.language or "unknown")
        for (i, t) in enumerate(
            [t for t in media_info.tracks if t.track_type == "Text"]
        )
        if t.streamorder
    ]
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


def _convert_file_to_mp4(input_filepath, output_filepath, subtitle_filepaths=[]):
    output_extension = os.path.splitext(output_filepath)[1]
    media_info = MediaInfo.parse(input_filepath)
    audio_codecs = [
        t.format.lower() for t in media_info.tracks if t.track_type == "Audio"
    ]
    needs_audio_conversion = not any("aac" in c for c in audio_codecs)
    n_sub_tracks = len([t for t in media_info.tracks if t.track_type == "Text"])
    if media_info.tracks:
        try:
            duration = next(t.duration for t in media_info.tracks if t.duration)
            duration = int(round(duration / 1000))
        except StopIteration:
            duration = None
        with open(f"{output_filepath}{settings.LOG_POSTFIX}", "w") as f:
            f.write(f"{duration}\r")
    return Popen(
        " ".join(
            [
                "ffmpeg -nostdin",
                f'-i "{input_filepath}"',
                " ".join([f'-f srt -i "{fn}"' for (lang, fn) in subtitle_filepaths]),
                "-err_detect ignore_err",
                "-map 0:v?",
                "-map 0:a?",
                "-map 0:s?" if n_sub_tracks > 0 else "",
                f"-acodec aac -ab {settings.AAC_BITRATE} -ac {settings.AAC_CHANNELS}"
                if needs_audio_conversion
                else "-acodec copy",
                "-vcodec copy",
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
                f'"{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}" 2>> "{output_filepath}{settings.LOG_POSTFIX}"',
                "&&",
                f'mv "{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}" "{output_filepath}"',
            ]
        ),
        shell=True,
    )

def _convert_file_to_hls_stream(input_filepath, output_filepath):
    log.debug(str([datetime.datetime.now(), "HLS", input_filepath, output_filepath]))
    media_info = MediaInfo.parse(input_filepath)
    audio_codecs = [
        t.format.lower() for t in media_info.tracks if t.track_type == "Audio"
    ]
    needs_audio_conversion = not any("aac" in c for c in audio_codecs)
    return Popen(
        " ".join(
            [
                "ffmpeg -nostdin",
                f'-i "{input_filepath}"',
                "-err_detect ignore_err",
                f"-acodec aac -ab {settings.AAC_BITRATE} -ac {settings.AAC_CHANNELS}"
                if needs_audio_conversion
                else "-acodec copy",
                "-vcodec copy",
                "-sn",
                "-segment_time 00:01:00",
                "-reset_timestamps 1",
                "-f segment",
                #f"-segment_list '{output_filepath}.tmp.m3u8'",
                "-v quiet -stats",
                f'"{output_filepath}_chunk%03d.ts" 2>> "{output_filepath}_hls_{settings.LOG_POSTFIX}"',
            ]
        ),
        shell=True,
    )


def get_conversion_progress(filepath):
    log_filepath = f"{filepath}{settings.LOG_POSTFIX}"
    if os.path.isfile(log_filepath):
        with open(log_filepath, "r") as f:
            lines = f.readlines()
            first_line = lines[0]
            last_line = lines[-1]
            duration = int(first_line)
            current_duration = re.search(r"time=\s*(\d\d\:\d\d\:\d\d)\s*", last_line)
            if current_duration:
                current_duration = current_duration.group(1)
                current_duration = time.strptime(
                    current_duration.split(",")[0], "%H:%M:%S"
                )
                current_duration = datetime.timedelta(
                    hours=current_duration.tm_hour,
                    minutes=current_duration.tm_min,
                    seconds=current_duration.tm_sec,
                ).total_seconds()
                return current_duration / duration
    return 0.0


def get_chunks(filepath):
    dirname = os.path.dirname(filepath)
    if not os.path.isdir(dirname):
        return []
    basename = os.path.basename(filepath)
    chunk_files = [f for f in os.listdir(dirname) if f.startswith(basename) and f.endswith(".ts")]
    chunk_files_with_duration = [(f, get_time_duration(os.path.join(dirname, f))) for f in chunk_files]
    return chunk_files_with_duration

def get_hls_playlist(filepath, prefix):
    chunks = get_chunks(filepath)
    return f"""#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:60
#EXT-X-ALLOW-CACHE:NO
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-START:TIME-OFFSET=-3600
""" + \
    "".join([f"""#EXTINF:{c[1]},
{c[0]}
""" for c in chunks])


def eligible_for_conversion(filepath):
    media_info = MediaInfo.parse(filepath)
    audio_tracks = [t for t in media_info.tracks if t.track_type == "Audio"]
    video_tracks = [t for t in media_info.tracks if t.track_type == "Video"]
    return len(audio_tracks) > 0 and len(video_tracks) > 0


def get_time_duration(filepath):
    duration_file = filepath + ".duration.txt"
    if os.path.isfile(duration_file):
        return float(Path(duration_file).read_text().strip())/1000
    media_info = MediaInfo.parse(filepath)
    duration = next((t.duration for t in media_info.tracks if t.duration and t.track_type == "Video"), None)
    with open(duration_file, "w") as f:
        f.write(str(duration))
    return get_time_duration(filepath)


class VideoConverter:
    file_conversions = {}
    lock = Lock()


    @threaded
    @log.catch_and_log_exceptions
    def convert_file(self, input_filepath, output_filepath):
        self.lock.acquire()

        if len(self.file_conversions.keys()) >= settings.MAX_PARALLEL_CONVERSIONS:
            return

        if self.file_conversions.get(output_filepath):
            self.lock.release()
            return
        else:
            self.file_conversions[output_filepath] = True
            self.lock.release()

        try:
            output_dir = os.path.dirname(output_filepath)
            os.makedirs(output_dir, exist_ok=True)

            # Gather subtitle files
            basename = os.path.basename(input_filepath)
            filename_without_extension = os.path.splitext(basename)[0]

            subtitle_filepaths = [
                (get_subtitle_language(os.path.basename(filepath)), filepath)
                for filepath in _recursive_filepaths(os.path.dirname(input_filepath))
                if (os.path.basename(filepath).lower()).startswith(
                    filename_without_extension.lower()
                )
                and filepath.endswith(".srt")
            ]

            conversion = _convert_file_to_mp4(
                input_filepath, output_filepath, subtitle_filepaths=subtitle_filepaths
            )
            conversion.wait()

            if conversion.returncode != 0:
                raise Exception(f"Conversion failed for {input_filepath}")

            _extract_subtitles_as_vtt(output_filepath).wait()

        finally:
            try:
                del self.file_conversions[output_filepath]
            except KeyError:
                pass

    @threaded
    @log.catch_and_log_exceptions
    def generate_hls_stream(self, input_filepath, output_filepath):
        log.debug(str([datetime.datetime.now(), "generate_hls_stream", input_filepath, output_filepath]))
        log.debug(str([datetime.datetime.now(), "lock_state", self.file_conversions]))
        self.lock.acquire()

        if len(self.file_conversions.keys()) >= settings.MAX_PARALLEL_CONVERSIONS:
            return

        if self.file_conversions.get(output_filepath):
            self.lock.release()
            return
        else:
            self.file_conversions[output_filepath] = True
            self.lock.release()

        try:
            log.debug(str([datetime.datetime.now(), "got_passed_lock", input_filepath, output_filepath]))

            self.file_conversions[output_filepath] = True

            output_dir = os.path.dirname(output_filepath)
            os.makedirs(output_dir, exist_ok=True)

            log.debug(str([datetime.datetime.now(), "STARTING CONVERSION", input_filepath, output_filepath]))
            conversion = _convert_file_to_hls_stream(
                input_filepath,
                output_filepath
            )
            log.debug(str([datetime.datetime.now(), "WAITING FOR CONVERSION", input_filepath, output_filepath]))
            conversion.wait()

            get_chunks(output_filepath)

            log.debug(str([datetime.datetime.now(), "DONE WAITING FOR CONVERSION", input_filepath, output_filepath]))

            if conversion.returncode != 0:
                log.debug(str([datetime.datetime.now(), "FAILED"]))
                time.sleep(20)
                raise Exception(f"Conversion failed for {input_filepath}: {conversion.returncode}")
            log.debug(str([datetime.datetime.now(), "ENDED GRACEFULLY"]))
        except Exception as e:
            print(e, flush=True)
        finally:
            try:
                log.debug(str([datetime.datetime.now(), "RELEASING LOCK", input_filepath, output_filepath]))
                del self.file_conversions[output_filepath]
            except KeyError:
                pass
