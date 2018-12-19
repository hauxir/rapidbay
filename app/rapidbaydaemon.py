import datetime
import os
import shutil
import time
from threading import Thread

import log
import settings
import subtitles
import torrent
import video_conversion
from common import threaded


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
    return (
        os.path.splitext(
            os.path.join(settings.OUTPUT_DIR, magnet_hash, os.path.basename(filepath))
        )[0]
        + ".mp4"
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
    CONVERTING = "converting"
    NO_TORRENT = "no_torrent"
    WAITING_FOR_METADATA = "waiting_for_metadata"
    FILE_NOT_FOUND = "file_not_found"
    DOWNLOADING_SUBTITLES_FROM_TORRENT = "downloading_subtitles_from_torrent"
    DOWNLOADING_SUBTITLES = "downloading_subtitles"
    WAITING_FOR_CONVERSION = "waiting_for_conversion"
    DOWNLOAD_FINISHED = "download_finished"
    DOWNLOADING = "downloading"


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
        )
        self.video_converter = video_conversion.VideoConverter()
        self.thread = Thread(target=self._loop, args=())
        self.thread.daemon = True

    def start(self):
        self.thread.start()

    @threaded
    @log.catch_and_log_exceptions
    def fetch_filelist_from_link(self, magnet_link):
        assert self.thread.is_alive()
        self.torrent_client.fetch_filelist_from_link(magnet_link)

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
        self.torrent_client.download_file(magnet_link, filename)

        h = self.torrent_client.torrents.get(magnet_hash)
        h.set_download_limit(settings.TORRENT_DOWNLOAD_LIMIT)
        h.set_upload_limit(settings.TORRENT_UPLOAD_LIMIT)

        if download_subtitles:
            for filename in _subtitle_filenames(
                self.torrent_client.torrents.get(magnet_hash), filename
            ):
                self.torrent_client.download_file(magnet_link, filename)

    def get_file_status(self, magnet_hash, filename):
        assert self.thread.is_alive()
        output_filepath = _get_output_filepath(magnet_hash, filename)
        if os.path.isfile(output_filepath):
            return dict(status=FileStatus.READY)
        if os.path.isfile(f"{output_filepath}{settings.INCOMPLETE_POSTFIX}"):
            progress = video_conversion.get_conversion_progress(output_filepath)
            return dict(status=FileStatus.CONVERTING, progress=progress)
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h:
            return dict(status=FileStatus.NO_TORRENT)
        if not h.has_metadata():
            return dict(status=FileStatus.WAITING_FOR_METADATA)
        files = list(h.get_torrent_info().files())
        i, f = torrent.get_index_and_file_from_files(h, filename)
        if f is None:
            return dict(status=FileStatus.FILE_NOT_FOUND)
        download_progress = h.file_progress()[i] / f.size
        if download_progress == 1:
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
            return dict(status=FileStatus.DOWNLOAD_FINISHED)
        return dict(
            status=FileStatus.DOWNLOADING,
            progress=download_progress,
            peers=h.status().num_peers,
        )

    def _download_external_subtitles(self, filepath):
        if self.subtitle_downloads.get(filepath):
            return
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.DOWNLOADING
        subtitles.download_all_subtitles(filepath)
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.FINISHED

    def _handle_torrent(self, magnet_hash):
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h:
            return
        files = [f for f in torrent.get_torrent_info(h).files()]
        filenames = [os.path.basename(f.path) for f in files]

        def is_state(filename, state):
            return self.get_file_status(magnet_hash, filename)["status"] == state

        if all(is_state(filename, "ready") for filename in filenames):
            self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
            for f in files:
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                self.subtitle_downloads.pop(filepath, None)
            return

        for i, f in enumerate(files):
            if h.file_priorities()[i] == 0:
                continue
            filename = os.path.basename(f.path)

            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)

            if is_state(filename, FileStatus.DOWNLOAD_FINISHED):
                self._download_external_subtitles(filepath)
            elif is_state(filename, FileStatus.WAITING_FOR_CONVERSION):
                output_filepath = _get_output_filepath(magnet_hash, filepath)
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                self.video_converter.convert_file(filepath, output_filepath)

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
                    self._handle_torrent(magnet_hash)
            except Exception as e:
                if "invalid torrent handle used" in str(e):
                    self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
                else:
                    raise e
        _remove_old_files_and_directories(
            settings.OUTPUT_DIR, settings.MAX_OUTPUT_FILE_AGE
        )
        _remove_old_files_and_directories(
            settings.FILELIST_DIR, settings.MAX_OUTPUT_FILE_AGE
        )

    def _loop(self):
        while True:
            self._heartbeat()
            time.sleep(1)
