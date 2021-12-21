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


def get_filepaths(magnet_hash):
    """
    Returns a list of filepaths for the given magnet hash.

    :param str
    magnet_hash: The hash of the magnet link to get filepaths for.
    """
    filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = f.read().replace("\n", "")
            return json.loads(data)


def _get_download_path(magnet_hash, filename):
    """
    Returns the full path to a file in the download directory for a given
    magnet hash.

    :param str magnet_hash: The unique identifier of the torrent.
    :param str filename: The name of the file to look for in that torrent's
    directory.
    """
    filepaths = get_filepaths(magnet_hash)
    if filepaths:
        torrent_path = next(fp for fp in filepaths if fp.endswith(filename))
        return os.path.join(f"{settings.DOWNLOAD_DIR}{magnet_hash}", torrent_path)


def _subtitle_filenames(h, filename):
    """
    Finds the subtitle filenames for a given torrent file.

    :param str h: The
    hash of the torrent to find subtitles for.
    :param str filename: The name of
    the video file in this torrent, without its extension.
    """
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
    """
    Return a list of indexes for the files in `torrent_info` that match the
    given subtitle filenames.

    :param torrent_info: The
    :class:`libtorrent.torrent_info` object to search through.
    :param filename:
    The filename (without path) of the video file to search for subtitles for,
    e.g., ``'videofile'`` or ``'videofile-eng'`` or ``'videofile-subbed-rus1',
    'videofile-subbed-rus2', ..., 'videofile-subbed']`` if there are multiple
    versions with different subtitles available (e.g., English and Russian).
    This is case sensitive!  If you want to use globbing wildcards, use
    :func:`.glob()`.
    """
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
    """
    _get_output_filepath(magnet_hash, filepath)

    Return the output file path
    for a given magnet hash and input file path.

        :param str magnet_hash:
    The hash of the torrent this output is associated with.
        :param str
    filepath: The absolute or relative path to an input video or audio stream.
    :returns: A string containing the absolute or relative output filename for
    this stream, without extension.

            If `isVideo` is True then it will
    be a mp4 extension; otherwise it will be in the same format as `filePath`.
    """
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
    """
    Removes files and directories from the given directory if they are older
    than the given age.

    :param dirname: The name of a directory to remove
    files and directories from.
    :type dirname: str
    :param max_age: The maximum
    age in hours for a file or directory to be kept before it is removed. Must
    be greater than 0. If 0, all files and directories will be removed
    immediately without checking their ages (useful for testing).
    """
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
        """
        Get the status of all files in a torrent.

        :param magnet_hash: The hash of
        the torrent.
        :type magnet_hash: str

            :returns dict -- A dictionary
        mapping filenames to their status as a tuple containing bytes downloaded,
        bytes total and whether it is seeding or downloading.  If no data has been
        downloaded for a file, then ``bytes_downloaded`` will be 0 and
        ``bytes_total`` will be None.  If the file is seeding then ``bytes_total``
        will be 0 and ``seeding=True`` .
        """
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

        if download_path:
            http_download_progress = self.http_downloader.downloads.get(download_path)
            if http_download_progress is None:
                cached_url = http_cache.get_cached_url(magnet_hash, filename)
                if cached_url:
                    self.http_downloader.download_file(cached_url, download_path)

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
        """
        Get the status of a file in a torrent.

        :param magnet_hash: The hash of the
        torrent.
        :type magnet_hash: str
        :param filename: The name of the file to
        get status for. This is relative to the root directory of the torrent and
        does not include any path separators (e.g., "/"). It can be None if you
        want to know whether there are any files in this torrent at all, but it's
        unlikely that you want that so much that you don't care what they're called
        or how many there are or anything like that, so I think it's more
        appropriate as an optional parameter instead of something required by
        default like some kind of `file` argument with no default value because
        "there aren't any files" is not useful information when trying to decide
        what action(s) your program should take next). If this parameter is None
        then only general information about this torrent will be returned;
        otherwise, detailed information about just this file will be returned
        (including its progress towards completion and its current download speed).
        Note also that if `filename` is specified then `magnet_hash` must also be
        specified since we need both parameters together for unique identification
        purposes even though only one seems necessary by itself (but again, I'm
        guessing most people would find it easier/more intuitive/more useful for
        them just explicitly specify both parameters anyway rather than leaving out
        one on accident). Also note that if multiple files exist with names
        matching those given in `filename`, which ones will actually match depends
        on their order within each individual .torrent metafile; thus using
        wildcards such as asterisks ("*") may help narrow down which matches apply
        but won't always work unless exact filenames are used instead.)  # noQA
        E501 line too long  # noQA E501 line too long  # noQA E501 line too long
        ...and probably other ways I haven't thought through yet... :type filename:
        str | NoneType

            :returns dict -- A dictionary containing keys
        corresponding to different statuses along with values indicating how far
        along each respective process has progressed according to these possible
        statuses:\n\n**status
        """
        assert self.thread.is_alive()
        filename_extension = os.path.splitext(filename)[1]
        output_filepath = _get_output_filepath(magnet_hash, filename)
        output_extension = os.path.splitext(output_filepath)[1]

        if os.path.isfile(output_filepath):
            if self.video_converter.file_conversions.get(output_filepath):
                return dict(status=FileStatus.FINISHING_UP)
            return dict(
                status=FileStatus.READY,
                filename=os.path.basename(output_filepath),
                subtitles=sorted(
                    [
                        f
                        for f in os.listdir(os.path.dirname(output_filepath))
                        if f.endswith(".vtt")
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

    def _download_external_subtitles(self, filepath):
        """
        Downloads external subtitles for the given filepath.

        :param str filepath:
        The path to the video file.
        """
        if self.subtitle_downloads.get(filepath):
            return
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.DOWNLOADING
        subtitles.download_all_subtitles(filepath)
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.FINISHED

    def _handle_torrent(self, magnet_hash):
        """
        _handle_torrent(magnet_hash)

        Handle a torrent with the given hash.

            *
        If all video files are ready, remove the torrent and copy them to their
        final destination.
            * If any video file is waiting for conversion, clear
        its download status and start converting it.
            * If any video file is
        waiting to be copied, copy it from its temporary location to its final
        destination.

          Args:
              magnet_hash (str): The hash of the torrent that
        needs handling.

          Returns: None if no error occurred during handling;
        otherwise an exception object containing information about what went wrong.
        """
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
                self._download_external_subtitles(filepath)
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
        """
        _heartbeat(self)

        For each magnet hash in the torrent client's list of
        hashes, check if the torrent is stale. If it is, remove it from the client.
        Otherwise, if it has metadata and hasn't been checked for a while (as
        defined by settings), check its status and download any new files that have
        appeared since last time we checked.
        """
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
