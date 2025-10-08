import datetime
import json
import os
import shutil
import time
from threading import Thread
from typing import Any, Dict, List, Optional

import http_cache
import log
import requests_unixsocket
import settings
import subtitles
import torrent
import video_conversion
from common import threaded
from flask import Flask, Response, jsonify, request
from http_downloader import HttpDownloader
from subtitles import get_subtitle_language

daemon: 'RapidBayDaemon'

class DaemonClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.session: requests_unixsocket.Session = requests_unixsocket.Session()

    def _get(self, path: str) -> Any:
        return self.session.get("http+unix://" + "%2Fapp%2Frapidbaydaemon.sock" + path).json()

    def _post(self, path: str, data: Dict[str, Any]) -> Any:
        return self.session.post("http+unix://" + "%2Fapp%2Frapidbaydaemon.sock" + path, json=data).json()

    def save_torrent_file(self, filepath: str) -> Dict[str, Any]:
        return self._post("/save_torrent_file", {'filepath': filepath})

    def fetch_filelist_from_link(self, magnet_link: str) -> Dict[str, Any]:
        return self._post("/fetch_filelist_from_link", {'magnet_link': magnet_link})

    def download_file(self, magnet_link: str, filename: str) -> Dict[str, Any]:
        return self._post("/download_file", {'magnet_link': magnet_link, 'filename': filename})

    def get_file_status(self, magnet_hash: str, filename: str) -> Dict[str, Any]:
        return self._get(f"/get_file_status/{magnet_hash}/{filename}")

    def downloads(self) -> Dict[str, Any]:
        return self._get("/downloads")

    def subtitle_downloads(self) -> Dict[str, Any]:
        return self._get("/subtitle_downloads")

    def session_torrents(self) -> Dict[str, Any]:
        return self._get("/session_torrents")

    def file_conversions(self) -> Dict[str, Any]:
        return self._get("/file_conversions")

    def http_downloads(self) -> Dict[str, Any]:
        return self._get("/http_downloads")


app: Flask = Flask(__name__)


def get_filepaths(magnet_hash: str) -> Optional[List[str]]:
    filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    if os.path.exists(filename):
        with open(filename) as f:
            data = f.read().replace("\n", "")
            return json.loads(data)
    return None


def _get_download_path(magnet_hash: str, filename: str) -> Optional[str]:
    filepaths = get_filepaths(magnet_hash)
    if filepaths:
        torrent_path = next(fp for fp in filepaths if fp.endswith(filename))
        return os.path.join(f"{settings.DOWNLOAD_DIR}{magnet_hash}", torrent_path)
    return None


def _subtitle_filenames(h: Any, filename: str) -> List[str]:
    files = torrent.get_torrent_info(h).files()
    filename_without_extension = os.path.splitext(filename)[0]
    subtitle_filenames: List[str] = []
    for f in files:
        basename = os.path.basename(f.path)
        basename_lower = basename.lower()
        if basename_lower.endswith(".srt") and basename_lower.startswith(
            filename_without_extension.lower()
        ):
            subtitle_filenames.append(basename)
    return subtitle_filenames


def _subtitle_indexes(h: Any, filename: str) -> List[int]:
    subtitle_filenames = _subtitle_filenames(h, filename)
    files = torrent.get_torrent_info(h).files()
    subtitle_set: List[str] = []
    subtitle_indexes: List[int] = []
    for i, f in enumerate(files):
        basename = os.path.basename(f.path).lower()
        if basename in subtitle_filenames and basename not in subtitle_set:
            subtitle_set.append(basename)
            subtitle_indexes.append(i)
    return subtitle_indexes


def _get_output_filepath(magnet_hash: str, filepath: str) -> str:
    extension = os.path.splitext(filepath)[1][1:]
    is_video = extension in settings.VIDEO_EXTENSIONS
    output_extension = "mp4" if is_video else extension
    return (
        os.path.splitext(
            os.path.join(settings.OUTPUT_DIR, magnet_hash, os.path.basename(filepath))
        )[0]
        + f".{output_extension}"
    )


def _remove_old_files_and_directories(dirname: str, max_age: int) -> None:
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


def _torrent_is_stale(h: Any) -> bool:
    return (time.time() - h.status().added_time) > 3600 * settings.MAX_TORRENT_AGE_HOURS


class FileStatus:
    READY: str = "ready"
    FINISHING_UP: str = "finishing_up"
    CONVERTING: str = "converting"
    CONVERSION_FAILED: str = "conversion_failed"
    WAITING_FOR_TORRENT: str = "waiting_for_torrent"
    WAITING_FOR_METADATA: str = "waiting_for_metadata"
    FILE_NOT_FOUND: str = "file_not_found"
    DOWNLOADING_SUBTITLES_FROM_TORRENT: str = "downloading_subtitles_from_torrent"
    DOWNLOADING_SUBTITLES: str = "downloading_subtitles"
    WAITING_FOR_CONVERSION: str = "waiting_for_conversion"
    DOWNLOAD_FINISHED: str = "download_finished"
    DOWNLOADING: str = "downloading"
    READY_TO_COPY: str = "ready_to_copy"


class SubtitleDownloadStatus:
    DOWNLOADING: str = "downloading"
    FINISHED: str = "finished"


class RapidBayDaemon:
    subtitle_downloads: Dict[str, str] = {}

    def __init__(self) -> None:
        self.torrent_client: torrent.TorrentClient = torrent.TorrentClient(
            listening_port=settings.TORRENT_LISTENING_PORT,
            dht_routers=settings.DHT_ROUTERS,
            filelist_dir=settings.FILELIST_DIR,
            download_dir=settings.DOWNLOAD_DIR,
            torrents_dir=settings.TORRENTS_DIR,
        )
        self.video_converter: video_conversion.VideoConverter = video_conversion.VideoConverter()
        self.thread: Thread = Thread(target=self._loop_wrapper, args=())
        self.thread.daemon = True
        self.http_downloader: HttpDownloader = HttpDownloader()

    def start(self) -> None:
        self.thread.start()

    def downloads(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        result: Dict[str, Dict[str, Dict[str, Any]]] = {}
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

    def session_torrents(self) -> List[str]:
        return [h.name() for h in self.torrent_client.session.get_torrents()]

    @threaded
    @log.catch_and_log_exceptions
    def fetch_filelist_from_link(self, magnet_link: str) -> None:
        assert self.thread.is_alive()
        print(f"fetch_filelist_from_link: {magnet_link}", flush=True)
        self.torrent_client.fetch_filelist_from_link(magnet_link)

    @log.catch_and_log_exceptions
    def save_torrent_file(self, filepath: str) -> None:
        self.torrent_client.save_torrent_file(filepath)

    @threaded
    @log.catch_and_log_exceptions
    def download_file(self, magnet_link: str, filename: str, download_subtitles: bool = True) -> None:
        assert self.thread.is_alive()
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
        h.set_download_limit(settings.TORRENT_DOWNLOAD_LIMIT)  # type: ignore
        h.set_upload_limit(settings.TORRENT_UPLOAD_LIMIT)  # type: ignore

        if download_subtitles:
            for subtitle_filename in _subtitle_filenames(
                self.torrent_client.torrents.get(magnet_hash), filename
            ):
                self.torrent_client.download_file(magnet_link, subtitle_filename)

    def get_file_status(self, magnet_hash: str, filename: str) -> Dict[str, Any]:
        assert self.thread.is_alive()
        filename_extension = os.path.splitext(filename)[1]
        output_filepath = _get_output_filepath(magnet_hash, filename)
        output_extension = os.path.splitext(output_filepath)[1]

        if os.path.isfile(output_filepath):
            if self.video_converter.file_conversions.get(output_filepath):
                return {'status': FileStatus.FINISHING_UP}
            base_filename = os.path.basename(output_filepath)
            base_filename_without_extension = os.path.splitext(base_filename)[0]
            return {
                'status': FileStatus.READY,
                'filename': base_filename,
                'subtitles': sorted(
                    [
                        f
                        for f in os.listdir(os.path.dirname(output_filepath))
                        if f.endswith(".vtt")
                        and f.startswith(base_filename_without_extension)
                    ],
                    key=lambda fn: fn.split("_")[-1],
                ),
                'supported': any(filename.endswith(ext) for ext in settings.SUPPORTED_EXTENSIONS)
            }
        if os.path.isfile(
            f"{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}"
        ):
            progress = video_conversion.get_conversion_progress(output_filepath)
            if not self.video_converter.file_conversions.get(output_filepath):
                return {'status': FileStatus.CONVERSION_FAILED}
            return {'status': FileStatus.CONVERTING, 'progress': progress}
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h:
            return {'status': FileStatus.WAITING_FOR_TORRENT}
        if not h.has_metadata():
            return {'status': FileStatus.WAITING_FOR_METADATA}
        files = list(h.get_torrent_info().files())
        i, f = torrent.get_index_and_file_from_files(h, filename)
        if f is None or i is None:
            return {'status': FileStatus.FILE_NOT_FOUND}
        download_progress = h.file_progress()[i] / f.size

        download_path = _get_download_path(magnet_hash, filename)
        http_progress = 0

        if download_path:
            http_progress = self.http_downloader.downloads.get(download_path, 0)

            # If HTTP download is complete, trust that over torrent progress
            if http_progress == 1:
                download_progress = 1
                # Trigger recheck but don't wait for it - let heartbeat handle it
                h.force_recheck()
            else:
                download_progress = max(http_progress, download_progress)

        if download_progress == 1:
            if filename_extension[1:] in settings.VIDEO_EXTENSIONS:
                all_torrent_subtitles_downloaded = all(
                    h.file_progress()[i] == files[i].size
                    for i in _subtitle_indexes(h, filename)
                )
                if not all_torrent_subtitles_downloaded:
                    return {'status': FileStatus.DOWNLOADING_SUBTITLES_FROM_TORRENT}
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                subtitle_download_status = self.subtitle_downloads.get(filepath)
                if subtitle_download_status == SubtitleDownloadStatus.DOWNLOADING:
                    return {'status': FileStatus.DOWNLOADING_SUBTITLES}
                if subtitle_download_status == SubtitleDownloadStatus.FINISHED:
                    return {'status': FileStatus.WAITING_FOR_CONVERSION}
            else:
                return {'status': FileStatus.READY_TO_COPY}
            return {'status': FileStatus.DOWNLOAD_FINISHED}
        return {
            'status': FileStatus.DOWNLOADING,
            'progress': download_progress,
            'peers': h.status().num_peers,
        }

    def _download_external_subtitles(self, filepath: str, skip: Optional[List[str]] = None) -> None:
        if skip is None:
            skip = []
        if self.subtitle_downloads.get(filepath):
            return
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.DOWNLOADING
        subtitles.download_all_subtitles(filepath, skip=skip)
        self.subtitle_downloads[filepath] = SubtitleDownloadStatus.FINISHED

    def _handle_torrent(self, magnet_hash: str) -> None:
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

        def is_state(filename: str, state: str) -> bool:
            return self.get_file_status(magnet_hash, filename)["status"] == state

        active_filenames = video_filenames if video_filenames else filenames

        if all(is_state(filename, FileStatus.READY) for filename in active_filenames):
            self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
            for f in files:
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                self.subtitle_downloads.pop(filepath, None)
                self.http_downloader.clear(filepath)
            return

        # Check if any HTTP downloads are active and trigger recheck
        needs_recheck = False
        for i, f in enumerate(files):
            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
            http_progress = self.http_downloader.downloads.get(filepath, -1)
            if http_progress > 0:
                needs_recheck = True
                if http_progress == 1:
                    # Only clear HTTP tracking if torrent now recognizes the file as complete
                    torrent_progress = h.file_progress()[i] / f.size if f.size > 0 else 0
                    if torrent_progress >= 0.99:  # Allow for small rounding errors
                        self.http_downloader.clear(filepath)
                        log.debug(f"HTTP cache download completed and recognized by torrent for {filepath}")

        if needs_recheck:
            h.force_recheck()

        for f in files:
            filename = os.path.basename(f.path)

            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
            output_filepath = _get_output_filepath(magnet_hash, filepath)

            if is_state(filename, FileStatus.DOWNLOAD_FINISHED):
                subtitle_filenames = _subtitle_filenames(h, filepath)
                available_subtitle_languages = [lang for lang in [get_subtitle_language(fn) for fn in subtitle_filenames] if lang]
                embedded_subtitle_languages = [lang for (_, lang) in video_conversion.get_sub_tracks(filepath)]
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
    def _heartbeat(self) -> None:
        # Process libtorrent session alerts for better monitoring
        self.torrent_client.process_alerts()

        for magnet_hash in list(self.torrent_client.torrents.keys()):
            h = self.torrent_client.torrents.get(magnet_hash)
            if not h:
                continue
            try:
                if _torrent_is_stale(h):
                    # Clear any HTTP downloads for this torrent before removing
                    for f in torrent.get_torrent_info(h).files():
                        filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                        self.subtitle_downloads.pop(filepath, None)
                        self.http_downloader.clear(filepath)
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

        # Clean up orphaned http_downloads entries
        active_hashes = set(self.torrent_client.torrents.keys())
        for filepath in list(self.http_downloader.downloads.keys()):
            if not any(hash in filepath for hash in active_hashes):
                self.http_downloader.clear(filepath)

    def _loop_wrapper(self) -> None:
        try:
            self._loop()
        except Exception as e:
            import traceback
            print(f"FATAL: Daemon thread crashed with exception: {e}", flush=True)
            print("Stack trace:", flush=True)
            traceback.print_exc()
            os._exit(1)
        print("FATAL: Daemon thread exited unexpectedly", flush=True)
        os._exit(1)

    def _loop(self) -> None:
        while True:
            self._heartbeat()
            time.sleep(1)


def start() -> None:
    global daemon
    daemon = RapidBayDaemon()
    daemon.start()


@app.route("/save_torrent_file", methods=["POST"])
def save_torrent_file_route() -> Response:
    filepath: str | None = request.json.get("filepath") if request.json else None  # type: ignore
    if filepath:
        daemon.save_torrent_file(filepath)
    return jsonify({})


@app.route("/fetch_filelist_from_link", methods=["POST"])
def fetch_filelist_from_link_route() -> Response:
    magnet_link: str | None = request.json.get("magnet_link") if request.json else None  # type: ignore
    if magnet_link:
        daemon.fetch_filelist_from_link(magnet_link)
    return jsonify({})


@app.route("/download_file", methods=["POST"])
def download_file_route() -> Response:
    magnet_link: str | None = request.json.get("magnet_link") if request.json else None  # type: ignore
    filename: str | None = request.json.get("filename") if request.json else None  # type: ignore
    if magnet_link and filename:
        daemon.download_file(magnet_link, filename)
    return jsonify({})


@app.route("/get_file_status/<string:magnet_hash>/<string:filename>")
def get_file_status_route(magnet_hash: str, filename: str) -> Response:
    response = daemon.get_file_status(magnet_hash, filename)
    return jsonify(**response)


@app.route("/downloads")
def downloads_route() -> Response:
    response = daemon.downloads()
    return jsonify(**response)


@app.route("/subtitle_downloads")
def subtitle_downloads_route() -> Response:
    response = daemon.subtitle_downloads
    return jsonify(**response)


@app.route("/session_torrents")
def session_torrents_route() -> Response:
    response = daemon.session_torrents()
    return jsonify(response)


@app.route("/file_conversions")
def file_conversions_route() -> Response:
    response = daemon.video_converter.file_conversions
    return jsonify(**response)


@app.route("/http_downloads")
def http_downloads_route() -> Response:
    response = daemon.http_downloader.downloads
    return jsonify(**response)


with app.app_context():
    start()
