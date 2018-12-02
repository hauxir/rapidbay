import datetime
import json
import os
import re
import shutil
import subprocess
import threading
import time
import traceback
from contextlib import contextmanager

import libtorrent as lt
from pymediainfo import MediaInfo

DOWNLOAD_DIR = "/tmp/downloads/"
OUTPUT_DIR = "/tmp/output/"
FILELIST_DIR = "/tmp/filelists/"
LOGFILE = "/tmp/rapidbay_errors.log"

DHT_ROUTERS = [
    "router.utorrent.com",
    "router.bittorrent.com",
    "dht.transmissionbt.com",
    "router.bitcomet.com",
    "dht.aelitis.com",
]

AAC_BITRATE = "128k"
SUPPORTED_EXTENSIONS = ["mp4", "mkv"]
INCOMPLETE_POSTFIX = ".incomplete.mp4"
LOG_POSTFIX = ".log"
MAX_TORRENT_AGE_HOURS = 10
MAX_OUTPUT_FILE_AGE = 10


def write_log():
    with open(LOGFILE, "a+") as f:
        f.write(traceback.format_exc() + "\n")


def catch_and_log_exceptions(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            write_log()

    return wrapper


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


class TorrentClient:
    file_downloads = {}
    locks = {}

    def __init__(self):
        self.thread = threading.Thread(target=self.loop, args=())
        self.thread.daemon = True
        self.session = lt.session()
        for router in DHT_ROUTERS:
            self.session.add_dht_router(router, 6881)
        self.session.start_dht()

    @contextmanager
    def lock(self, magnet_hash):
        self.get_lock(magnet_hash)
        yield
        self.release_lock(magnet_hash)

    def get_hash(self, magnet_link):
        if not magnet_link.startswith("magnet:?xt=urn:btih:"):
            raise Exception("Invalid magnet link")
        return magnet_link[
            magnet_link.find("btih:") + 5 : magnet_link.find("&")
            if "&" in magnet_link
            else len(magnet_link)
        ]

    def get_torrent_info(self, h):
        while not h.has_metadata():
            time.sleep(1)
        return h.get_torrent_info()

    def prioritize_files(self, h, priorities):
        h.prioritize_files(priorities)
        while h.file_priorities() != priorities:
            time.sleep(1)

    def get_lock(self, magnet_hash):
        thread_id = threading.get_ident()
        while self.locks.get(magnet_hash) not in [None, thread_id, None]:
            time.sleep(1)
        self.locks[magnet_hash] = thread_id

    def release_lock(self, magnet_hash):
        del self.locks[magnet_hash]

    def lock_available(self, magnet_hash):
        thread_id = threading.get_ident()
        return self.locks.get(magnet_hash, thread_id) == thread_id

    @threaded
    @catch_and_log_exceptions
    def write_filelist_to_disk(self, magnet_link):
        magnet_hash = self.get_hash(magnet_link)
        filename = os.path.join(FILELIST_DIR, magnet_hash)
        with self.lock(magnet_hash):
            h = self.file_downloads.get(magnet_hash)
            if not h:
                h = lt.add_magnet_uri(
                    self.session,
                    magnet_link,
                    dict(save_path=os.path.join(DOWNLOAD_DIR, magnet_hash)),
                )
                self.file_downloads[magnet_hash] = h
                files = self.get_torrent_info(h).files()
                self.prioritize_files(h, [0] * len(files))
            result = sorted(
                [
                    os.path.basename(os.path.normpath(f.path))
                    for f in self.get_torrent_info(h).files()
                    if any(f.path.endswith(f".{ext}") for ext in SUPPORTED_EXTENSIONS)
                ]
            )
        try:
            os.makedirs(os.path.dirname(filename))
        except FileExistsError:
            pass
        with open(filename, "w") as f:
            f.write(json.dumps(result))

    def get_files_from_link(self, magnet_link):
        magnet_hash = self.get_hash(magnet_link)
        filename = os.path.join(FILELIST_DIR, magnet_hash)
        if os.path.isfile(filename):
            try:
                with open(filename, "r") as f:
                    data = f.read().replace("\n", "")
                    json.loads(data)
                    return
            except json.decoder.JSONDecodeError:
                os.remove(filename)
        self.write_filelist_to_disk(magnet_link)

    def needs_conversion(self, magnet_hash, filepath):
        output_filepath = self.get_output_filepath(magnet_hash, filepath)
        return not os.path.exists(output_filepath) and not os.path.exists(
            f"{output_filepath}{INCOMPLETE_POSTFIX}"
        )

    def convert_file(self, magnet_hash, filepath):
        try:
            os.makedirs(os.path.join(OUTPUT_DIR, magnet_hash))
        except FileExistsError:
            pass
        input_dir = os.path.dirname(filepath)
        basename = os.path.basename(filepath)
        filename_without_extension = os.path.splitext(basename)[0]
        media_info = MediaInfo.parse(filepath)
        audio_codecs = [
            t.codec.lower() for t in media_info.tracks if t.track_type == "Audio"
        ]
        needs_audio_conversion = not any("aac" in c for c in audio_codecs)
        output_filepath = self.get_output_filepath(magnet_hash, filepath)
        output_dir = os.path.join(OUTPUT_DIR, magnet_hash)
        try:
            os.makedirs(output_dir)
        except FileExistsError:
            pass
        if media_info.tracks:
            try:
                duration = next(t.duration for t in media_info.tracks if t.duration)
                duration = int(round(duration / 1000))
            except StopIteration:
                duration = None
            with open(f"{output_filepath}{LOG_POSTFIX}", "w+") as f:
                f.write(f"{duration}\r")

        subtitle_files = [
            os.path.join(input_dir, fn)
            for fn in os.listdir(os.path.dirname(filepath))
            if fn.startswith(filename_without_extension) and fn.endswith(".srt")
        ]

        subprocess.Popen(
            " ".join(
                [
                    "ffmpeg",
                    f'-i "{filepath}"',
                    " ".join([f'-f srt -i "{fn}"' for fn in subtitle_files]),
                    f"-acodec aac -ab {AAC_BITRATE}"
                    if needs_audio_conversion
                    else "-acodec copy",
                    "-vcodec copy",
                    "-v quiet -stats",
                    "-movflags faststart",
                    "-c:s mov_text",
                    f'"{output_filepath}{INCOMPLETE_POSTFIX}" 2>> "{output_filepath}{LOG_POSTFIX}"',
                    "&&",
                    f'mv "{output_filepath}.incomplete.mp4" "{output_filepath}"',
                ]
            ),
            shell=True,
        )

    def subtitle_indexes(self, h, filename):
        files = self.get_torrent_info(h).files()
        filename_without_extension = os.path.splitext(filename)[0]
        subtitle_indexes = []
        for i, f in enumerate(files):
            basename = os.path.basename(f.path)
            if basename.endswith(".srt") and basename.startswith(
                filename_without_extension
            ):
                subtitle_indexes.append(i)
        return subtitle_indexes

    def handle_torrent(self, magnet_hash, h):
        is_finished = (
            str(h.status().state) in ["finished", "seeding"]
            or sum(h.file_priorities()) == 0
        )
        needs_conversion = False
        files = list(enumerate([f for f in self.get_torrent_info(h).files()]))
        for i, f in files:
            if h.file_priorities()[i] == 0:
                continue
            is_video_file = any(
                f.path.endswith(f".{ext}") for ext in SUPPORTED_EXTENSIONS
            )
            is_finished_downloading = h.file_progress()[i] == f.size
            basename = os.path.basename(f.path)
            all_subtitles_downloaded = all(
                [
                    h.file_progress()[i] == files[i][1].size
                    for i in self.subtitle_indexes(h, basename)
                ]
            )
            if is_video_file and is_finished_downloading and all_subtitles_downloaded:
                filepath = os.path.join(DOWNLOAD_DIR, magnet_hash, f.path)
                output_filepath = self.get_output_filepath(magnet_hash, filepath)
                try:
                    os.makedirs(os.path.dirname(output_filepath))
                except FileExistsError:
                    pass
                if self.needs_conversion(magnet_hash, filepath):
                    self.convert_file(magnet_hash, filepath)
                    needs_conversion = True
        if self.lock_available(magnet_hash) and is_finished and not needs_conversion:
            self.remove_torrent(magnet_hash)

    def remove_torrent(self, magnet_hash):
        try:
            h = self.file_downloads[magnet_hash]
        except KeyError:
            return
        try:
            self.session.remove_torrent(h)
        except:
            pass
        del self.file_downloads[magnet_hash]
        try:
            shutil.rmtree(os.path.join(DOWNLOAD_DIR, magnet_hash))
        except FileNotFoundError:
            pass

    def get_output_filepath(self, magnet_hash, filepath):
        return (
            os.path.splitext(
                os.path.join(OUTPUT_DIR, magnet_hash, os.path.basename(filepath))
            )[0]
            + ".mp4"
        )

    def clean_dir(self, dirname):
        try:
            dirs = os.listdir(dirname)
        except FileNotFoundError:
            return
        for subdir in dirs:
            modified = datetime.datetime.strptime(
                time.ctime(os.path.getmtime(os.path.join(dirname, subdir))),
                "%a %b %d %H:%M:%S %Y",
            )
            diff = datetime.datetime.now() - modified
            days, seconds = diff.days, diff.seconds
            hours = days * 24 + seconds
            hours = days * 24 + seconds // 3600
            if hours > MAX_OUTPUT_FILE_AGE:
                shutil.rmtree(os.path.join(dirname, subdir))

    def cleanup_output_dir(self):
        self.clean_dir(OUTPUT_DIR)

    def cleanup_filelist_dir(self):
        self.clean_dir(FILELIST_DIR)

    @catch_and_log_exceptions
    def heartbeat(self):
        for magnet_hash, h in list(self.file_downloads.items()):
            with self.lock(magnet_hash):
                try:
                    torrent_is_stale = (
                        time.time() - h.status().added_time
                    ) > 3600 * MAX_TORRENT_AGE_HOURS
                    if h.has_metadata():
                        self.handle_torrent(magnet_hash, h)
                    elif torrent_is_stale:
                        self.remove_torrent(magnet_hash)
                except Exception as e:
                    if "invalid torrent handle used" in str(e):
                        self.remove_torrent(magnet_hash)
                    else:
                        raise e
        self.cleanup_output_dir()
        self.cleanup_filelist_dir()

    def loop(self):
        while True:
            self.heartbeat()
            time.sleep(1)

    def get_files(self, magnet_hash):
        filename = os.path.join(FILELIST_DIR, magnet_hash)
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                data = f.read().replace("\n", "")
                return json.loads(data)
        return None

    @threaded
    @catch_and_log_exceptions
    def download_file(self, magnet_link, filename):
        magnet_hash = self.get_hash(magnet_link)
        with self.lock(magnet_hash):
            h = self.file_downloads.get(magnet_hash)
            if not h:
                h = lt.add_magnet_uri(
                    self.session,
                    magnet_link,
                    dict(save_path=os.path.join(DOWNLOAD_DIR, magnet_hash)),
                )
                self.file_downloads[magnet_hash] = h
                while True:
                    try:
                        files = self.get_torrent_info(h).files()
                        break
                    except RuntimeError:
                        continue
                file_priorities = [0] * len(files)
                for i, f in enumerate(files):
                    if f.path.endswith(filename):
                        file_priorities[i] = 4
                        break
                for i in self.subtitle_indexes(h, filename):
                    file_priorities[i] = 4
                self.prioritize_files(h, file_priorities)
            else:
                files = self.get_torrent_info(h).files()
                file_priorities = h.file_priorities()
                for i, f in enumerate(files):
                    if f.path.endswith(filename):
                        file_priorities[i] = 4
                        break
                for i in self.subtitle_indexes(h, filename):
                    file_priorities[i] = 4
                self.prioritize_files(h, file_priorities)
        self.write_filelist_to_disk(magnet_link)
        return h

    def get_conversion_progress(self, magnet_hash, filename):
        output_filepath = self.get_output_filepath(magnet_hash, filename)
        log_filepath = f"{output_filepath}{LOG_POSTFIX}"
        if os.path.isfile(log_filepath):
            try:
                with open(log_filepath, "r") as f:
                    lines = f.readlines()
                    first_line = lines[0]
                    last_line = lines[-1]
                    duration = int(first_line)
                    current_duration = re.search(
                        r"time=\s*(\d\d\:\d\d\:\d\d)\s*", last_line
                    ).group(1)
                    current_duration = time.strptime(
                        current_duration.split(",")[0], "%H:%M:%S"
                    )
                    current_duration = datetime.timedelta(
                        hours=current_duration.tm_hour,
                        minutes=current_duration.tm_min,
                        seconds=current_duration.tm_sec,
                    ).total_seconds()
                return current_duration / duration
            except Exception as e:
                write_log()
        return 0.0

    def get_file_status(self, magnet_hash, filename):
        h = self.file_downloads.get(magnet_hash)
        output_filepath = self.get_output_filepath(magnet_hash, filename)
        if os.path.isfile(output_filepath):
            return dict(status="ready")
        if os.path.isfile(f"{output_filepath}{INCOMPLETE_POSTFIX}"):
            progress = self.get_conversion_progress(magnet_hash, filename)
            return dict(status="converting", progress=progress)
        if not h:
            return dict(status="no_torrent")
        if not h.has_metadata():
            return dict(status="waiting_for_metadata")
        files = h.get_torrent_info().files()
        try:
            i, f = next(
                (i, f) for (i, f) in enumerate(files) if f.path.endswith(filename)
            )
        except StopIteration:
            return dict(status="file_not_found")
        percentage = h.file_progress()[i] / f.size
        return dict(
            status="downloading", progress=percentage, peers=h.status().num_peers
        )

    def start(self):
        self.thread.start()
