import cachetools.func
import json
import datetime
import os
import shutil
import time
from threading import Thread

import http_cache
import log
import settings
import subtitles
import torrent
import video_conversion
from http_downloader import HttpDownloader
from common import threaded


@cachetools.func.ttl_cache(ttl=60*60)
def _open_json_file(filepath):
    with open(filepath, "r") as f:
        data = f.read().replace("\n", "")
        return json.loads(data)


def get_filepaths(magnet_hash):
    filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    if os.path.exists(filename):
        return _open_json_file(filename)


def _get_download_path(magnet_hash, filename):
    filepaths = get_filepaths(magnet_hash)
    if filepaths:
        torrent_path = next(fp for fp in filepaths if fp.endswith(filename))
        return os.path.join(f"{settings.DOWNLOAD_DIR}{magnet_hash}", torrent_path)


def _subtitle_filenames(h, filename):
    files = torrent.get_torrent_info(h).files()
    filename_without_extension = os.path.splitext(filename)[0]
    subtitle_filenames = []
    for f in files:
        basename = os.path.basename(f.path)
        basename_lower = basename.lower()
        if basename_lower.endswith(".srt") and basename_lower.startswith(
            filename_without_extension.lower()
        ):
            subtitle_filenames.append(basename)
    return subtitle_filenames


def _subtitle_indexes(h, filename):
    subtitle_filenames = _subtitle_filenames(h, filename)
    files = torrent.get_torrent_info(h).files()
    subtitle_set = []
    subtitle_indexes = []
    for i, f in enumerate(files):
        basename = os.path.basename(f.path).lower()
        if basename in subtitle_filenames and basename not in subtitle_set:
            subtitle_set.append(basename)
            subtitle_indexes.append(i)
    return subtitle_indexes


def _get_output_filepath(magnet_hash, filepath):
    extension = os.path.splitext(filepath)[1][1:]
    is_video = extension in settings.VIDEO_EXTENSIONS
    output_extension = "mp4" if is_video else extension
    return (
        os.path.splitext(
            os.path.join(settings.OUTPUT_DIR, magnet_hash, os.path.basename(filepath))
        )[0]
        + f".{output_extension}"
    )


def _remove_old_files_and_directories(dirname, max_age):
    try:
        subpaths = os.listdir(dirname)
    except FileNotFoundError:
        return
    for subpath in subpaths:
        modified = datetime.datetime.strptime(
            time.ctime(os.path.getmtime(os.path.join(dirname, subpath))),
            "%a %b %d %H:%M:%S %Y",
        )
        diff = datetime.datetime.now() - modified
        days, seconds = diff.days, diff.seconds
        hours = days * 24 + seconds
        hours = days * 24 + seconds // 3600
        if hours > max_age:
            path = os.path.join(dirname, subpath)
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)


def _torrent_is_stale(h):
    return (time.time() - h.status().added_time) > 3600 * settings.MAX_TORRENT_AGE_HOURS


class FileStatus:
    READY = "ready"
    FINISHING_UP = "finishing_up"
    CONVERTING = "converting"
    CONVERSION_FAILED = "conversion_failed"
    WAITING_FOR_TORRENT = "waiting_for_torrent"
    WAITING_FOR_METADATA = "waiting_for_metadata"
    FILE_NOT_FOUND = "file_not_found"
    DOWNLOADING_SUBTITLES_FROM_TORRENT = "downloading_subtitles_from_torrent"
    DOWNLOADING_SUBTITLES = "downloading_subtitles"
    WAITING_FOR_CONVERSION = "waiting_for_conversion"
    DOWNLOAD_FINISHED = "download_finished"
    DOWNLOADING = "downloading"
    READY_TO_COPY = "ready_to_copy"


class SubtitleDownloadStatus:
    DOWNLOADING = "downloading"
    FINISHED = "finished"


class RapidBayDaemon:
    subtitle_downloads = {}

    def __init__(self):
        self.torrent_client = torrent.TorrentClient(
            listening_port=settings.TORRENT_LISTENING_PORT,
            dht_routers=settings.DHT_ROUTERS,
            filelist_dir=settings.FILELIST_DIR,
            download_dir=settings.DOWNLOAD_DIR,
            torrents_dir=settings.TORRENTS_DIR,
        )
        self.video_converter = video_conversion.VideoConverter()
        self.thread = Thread(target=self._loop, args=())
        self.thread.daemon = True
        self.http_downloader = HttpDownloader()

    def start(self):
        self.thread.start()

    def downloads(self):
        result = {}
        for magnet_hash, h in self.torrent_client.torrents.items():
            result[magnet_hash] = {}
            files = torrent.get_torrent_info(h).files()
            file_priorities = h.file_priorities()
            for priority, f in zip(list(file_priorities), list(files)):
                if priority == 0:
                    continue
                filename = os.path.basename(f.path)
                result[magnet_hash][filename] = self.get_file_status(
                    magnet_hash, filename
                )
        return result

    def session_torrents(self):
        return [h.name() for h in self.torrent_client.session.get_torrents()]

    @threaded
    @log.catch_and_log_exceptions
    def fetch_filelist_from_link(self, magnet_link):
        assert self.thread.is_alive()

        magnet_hash = torrent.get_hash(magnet_link)
        filename = os.path.join(settings.FILELIST_DIR, magnet_hash)

        if not os.path.exists(filename):
            cached_filelist = http_cache.get_cached_filelist(magnet_hash)
            if cached_filelist:
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w") as f:
                    f.write(json.dumps(cached_filelist))

            self.torrent_client.fetch_filelist_from_link(magnet_link)

    @log.catch_and_log_exceptions
    def save_torrent_file(self, filepath):
        self.torrent_client.save_torrent_file(filepath)

    @threaded
    @log.catch_and_log_exceptions
    def download_file(self, magnet_link, filename, download_subtitles=True):
        assert self.thread.is_alive()
        assert any(filename.endswith(ext) for ext in settings.SUPPORTED_EXTENSIONS)
        magnet_hash = torrent.get_hash(magnet_link)
        if self.get_file_status(magnet_hash, filename)["status"] in [
            FileStatus.READY,
            FileStatus.CONVERTING,
        ]:
            return

        download_path = _get_download_path(magnet_hash, filename)

        self.torrent_client.download_file(magnet_link, filename)

        h = self.torrent_client.torrents.get(magnet_hash)
        h.set_download_limit(settings.TORRENT_DOWNLOAD_LIMIT)
        h.set_upload_limit(settings.TORRENT_UPLOAD_LIMIT)

        if download_path:
            http_download_progress = self.http_downloader.downloads.get(download_path)
            if http_download_progress is None:
                cached_url = http_cache.get_cached_url(magnet_hash, filename)
                if cached_url:
                    self.http_downloader.download_file(cached_url, download_path)

        if download_subtitles:
            for filename in _subtitle_filenames(
                self.torrent_client.torrents.get(magnet_hash), filename
            ):
                self.torrent_client.download_file(magnet_link, filename)

    def get_file_status(self, magnet_hash, filename):
        assert self.thread.is_alive()
        filename_extension = os.path.splitext(filename)[1]
        output_filepath = _get_output_filepath(magnet_hash, filename)
        output_extension = os.path.splitext(output_filepath)[1]

        if os.path.isfile(output_filepath):
            if self.video_converter.file_conversions.get(output_filepath):
                return dict(status=FileStatus.FINISHING_UP)
            fn_without_extension = os.path.splitext(filename)[0]
            return dict(
                status=FileStatus.READY,
                filename=os.path.basename(output_filepath),
                subtitles=sorted(
                    [
                        f
                        for f in os.listdir(os.path.dirname(output_filepath))
                        if f.endswith(".vtt") and f.startswith(fn_without_extension)
                    ],
                    key=lambda fn: fn.split("_")[-1],
                ),
            )
        if os.path.isfile(
            f"{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}"
        ):
            progress = video_conversion.get_conversion_progress(output_filepath)
            if not self.video_converter.file_conversions.get(output_filepath):
                return dict(status=FileStatus.CONVERSION_FAILED)
            return dict(status=FileStatus.CONVERTING, progress=progress)
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h:
            return dict(status=FileStatus.WAITING_FOR_TORRENT)
        if not h.has_metadata():
            return dict(status=FileStatus.WAITING_FOR_METADATA)
        files = list(h.get_torrent_info().files())
        i, f = torrent.get_index_and_file_from_files(h, filename)
        if f is None:
            return dict(status=FileStatus.FILE_NOT_FOUND)
        download_progress = h.file_progress()[i] / f.size

        download_path = _get_download_path(magnet_hash, filename)

        if download_path:
            download_progress = max(
                self.http_downloader.downloads.get(download_path, 0), download_progress
            )

        if download_progress == 1:
            if filename_extension[1:] in settings.VIDEO_EXTENSIONS:
                all_torrent_subtitles_downloaded = all(
                    h.file_progress()[i] == files[i].size
                    for i in _subtitle_indexes(h, filename)
                )
                if not all_torrent_subtitles_downloaded:
                    return dict(status=FileStatus.DOWNLOADING_SUBTITLES_FROM_TORRENT)
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                subtitle_download_status = self.subtitle_downloads.get(filepath)
                if subtitle_download_status == SubtitleDownloadStatus.DOWNLOADING:
                    return dict(status=FileStatus.DOWNLOADING_SUBTITLES)
                if subtitle_download_status == SubtitleDownloadStatus.FINISHED:
                    return dict(status=FileStatus.WAITING_FOR_CONVERSION)
            else:
                return dict(status=FileStatus.READY_TO_COPY)
            return dict(status=FileStatus.DOWNLOAD_FINISHED)
        return dict(
            status=FileStatus.DOWNLOADING,
            progress=download_progress,
            peers=h.status().num_peers,
        )

    def _download_external_subtitles(self, filepath, skip=[]):
        if self.subtitle_downloads.get(filepath):
            return
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.DOWNLOADING
        subtitles.download_all_subtitles(filepath, skip=skip)
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.FINISHED

    def _handle_torrent(self, magnet_hash):
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h:
            return
        file_priorities = h.file_priorities()
        files = [
            f
            for priority, f in zip(file_priorities, torrent.get_torrent_info(h).files())
            if priority != 0
        ]
        filenames = [os.path.basename(f.path) for f in files]
        video_filenames = [
            fn
            for fn in filenames
            if any(fn.endswith(ext) for ext in settings.SUPPORTED_EXTENSIONS)
        ]

        def is_state(filename, state):
            return self.get_file_status(magnet_hash, filename)["status"] == state

        if all(is_state(filename, FileStatus.READY) for filename in video_filenames):
            self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
            for f in files:
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                self.subtitle_downloads.pop(filepath, None)
            return

        for f in files:
            filename = os.path.basename(f.path)

            if not any(filename.endswith(ext) for ext in settings.SUPPORTED_EXTENSIONS):
                continue

            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
            output_filepath = _get_output_filepath(magnet_hash, filepath)

            if is_state(filename, FileStatus.DOWNLOAD_FINISHED):
                subtitle_filenames = _subtitle_filenames(h, filepath)
                available_subtitle_languages = [lang for lang in [get_subtitle_language(fn) for fn in subtitle_filenames] if lang]
                embedded_subtitle_languages = [lang for (i,lang) in video_conversion.get_sub_tracks(filepath)]
                self._download_external_subtitles(filepath, skip=available_subtitle_languages + embedded_subtitle_languages)
            elif is_state(filename, FileStatus.WAITING_FOR_CONVERSION):
                self.http_downloader.clear(filepath)
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                self.video_converter.convert_file(filepath, output_filepath)
            elif is_state(filename, FileStatus.READY_TO_COPY) or is_state(
                filename, FileStatus.CONVERSION_FAILED
            ):
                output_dir = os.path.dirname(output_filepath)
                os.makedirs(output_dir, exist_ok=True)
                shutil.copy(filepath, output_filepath)

    @log.catch_and_log_exceptions
    def _heartbeat(self):
        for magnet_hash in list(self.torrent_client.torrents.keys()):
            h = self.torrent_client.torrents.get(magnet_hash)
            if not h:
                continue
            try:
                if _torrent_is_stale(h):
                    self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
                elif h.has_metadata():
                    with self.torrent_client.locks.lock(magnet_hash):
                        self._handle_torrent(magnet_hash)
            except Exception as e:
                raise e
        _remove_old_files_and_directories(
            settings.OUTPUT_DIR, settings.MAX_OUTPUT_FILE_AGE
        )
        _remove_old_files_and_directories(
            settings.FILELIST_DIR, settings.MAX_OUTPUT_FILE_AGE
        )
        _remove_old_files_and_directories(
            settings.DOWNLOAD_DIR, settings.MAX_OUTPUT_FILE_AGE
        )
        _remove_old_files_and_directories(
            settings.TORRENTS_DIR, settings.MAX_OUTPUT_FILE_AGE
        )

    def _loop(self):
        while True:
            self._heartbeat()
            time.sleep(1)
