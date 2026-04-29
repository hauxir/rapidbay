import datetime
import json
import os
import shutil
import time
from threading import Event, Thread
from typing import Any, Dict, List, Set

import http_cache
import log
import settings
import subtitles
import torrent
import video_conversion
from common import normalize_filename, threaded
from http_downloader import HttpDownloader
from subtitles import get_subtitle_language


def get_filepaths(magnet_hash: str) -> List[str] | None:
    filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    if os.path.exists(filename):
        with open(filename) as f:
            data = f.read().replace("\n", "")
            return json.loads(data)
    return None


def _get_download_path(magnet_hash: str, filename: str) -> str | None:
    filepaths = get_filepaths(magnet_hash)
    if filepaths:
        normalized = normalize_filename(filename)
        torrent_path = next(
            (fp for fp in filepaths if normalize_filename(fp).endswith(normalized)),
            None,
        )
        if torrent_path is None:
            return None
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
        path = os.path.join(dirname, subpath)
        try:
            modified = datetime.datetime.strptime(
                time.ctime(os.path.getmtime(path)),
                "%a %b %d %H:%M:%S %Y",
            )
        except FileNotFoundError:
            continue
        diff = datetime.datetime.now() - modified
        days, seconds = diff.days, diff.seconds
        hours = days * 24 + seconds // 3600
        if hours > max_age:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.isfile(path):
                    os.remove(path)
            except FileNotFoundError:
                pass


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
    def __init__(self) -> None:
        self.subtitle_downloads: Dict[str, str] = {}
        self.torrent_client: torrent.TorrentClient = torrent.TorrentClient(
            listening_port=settings.TORRENT_LISTENING_PORT,
            dht_routers=settings.DHT_ROUTERS,
            filelist_dir=settings.FILELIST_DIR,
            download_dir=settings.DOWNLOAD_DIR,
            torrents_dir=settings.TORRENTS_DIR,
        )
        self.video_converter: video_conversion.VideoConverter = video_conversion.VideoConverter()
        # Files we're fetching via HTTP (Real-Debrid). Tracked separately from
        # libtorrent's `file_priorities`, because we set those files to
        # priority 0 to keep libtorrent from writing the same path in parallel
        # — the daemon's lifecycle code uses `priority != 0` as a proxy for
        # "user-selected", which would otherwise drop these files from
        # `active_filenames` and remove the torrent (with files) mid-download.
        self._http_served: Dict[str, Set[str]] = {}
        self._stop_event: Event = Event()
        self.thread: Thread = Thread(target=self._loop_wrapper, args=())
        self.thread.daemon = True
        self.http_downloader: HttpDownloader = HttpDownloader()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self.thread.join(timeout=5.0)

    def downloads(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        result: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for magnet_hash, h in self.torrent_client.torrents.items():
            result[magnet_hash] = {}
            files = torrent.get_torrent_info(h).files()
            file_priorities = h.file_priorities()
            http_served_names = self._http_served.get(magnet_hash, set())
            for priority, f in zip(list(file_priorities), list(files), strict=False):
                filename = os.path.basename(f.path)
                if priority == 0 and filename not in http_served_names:
                    continue
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

        using_http = False
        if download_path:
            if self.http_downloader.downloads.get(download_path) is not None:
                using_http = True
            else:
                cached_url = http_cache.get_cached_url(magnet_hash, filename)
                if cached_url:
                    self.http_downloader.download_file(cached_url, download_path)
                    using_http = True

        self.torrent_client.download_file(magnet_link, filename)

        h = self.torrent_client.torrents.get(magnet_hash)
        h.set_download_limit(settings.TORRENT_DOWNLOAD_LIMIT)  # type: ignore
        h.set_upload_limit(settings.TORRENT_UPLOAD_LIMIT)  # type: ignore

        # Stop libtorrent from also fetching this file from peers — concurrent
        # writes between urlretrieve and libtorrent corrupted the file in
        # practice. The file stays in `_http_served` so the daemon's
        # priority-based filters still treat it as user-selected.
        # Hold the per-torrent lock around the read-modify-write of priorities;
        # other code paths (torrent_client.download_file,
        # torrent_client.get_sequential_bytes, the heartbeat failover) all
        # mutate the same handle under this lock.
        if using_http and h is not None:
            with self.torrent_client.locks.lock(magnet_hash):
                self._http_served.setdefault(magnet_hash, set()).add(filename)
                i, _ = torrent.get_index_and_file_from_files(h, filename)
                if i is not None:
                    priorities = list(h.file_priorities())
                    priorities[i] = 0
                    torrent.prioritize_files(h, priorities)

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
            download_progress = 1 if http_progress == 1 else max(http_progress, download_progress)

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

    def _download_external_subtitles(self, filepath: str, skip: List[str] | None = None) -> None:
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
        http_served_names = self._http_served.get(magnet_hash, set())
        # Include priority-0 files that we're HTTP-serving — see _http_served's
        # comment on RapidBayDaemon.
        files = [
            f
            for priority, f in zip(file_priorities, torrent.get_torrent_info(h).files(), strict=False)
            if priority != 0 or os.path.basename(f.path) in http_served_names
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
            self._http_served.pop(magnet_hash, None)
            for f in files:
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                self.subtitle_downloads.pop(filepath, None)
                self.http_downloader.clear(filepath)
            return

        # Iterate over the unfiltered torrent files so `file_progress` indexing
        # matches libtorrent's view; `files` above is filtered. Skip
        # HTTP-served files here — their libtorrent progress is pinned at 0
        # (we set priority 0), so the >=0.99 check will never fire and the
        # entry would be cleared while the daemon's state machine still
        # depends on http_progress == 1 to advance past DOWNLOADING. It's
        # cleared on the WAITING_FOR_CONVERSION transition below instead.
        file_progress = h.file_progress()
        for i, f in enumerate(torrent.get_torrent_info(h).files()):
            if file_priorities[i] == 0:
                continue
            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
            if self.http_downloader.downloads.get(filepath, -1) == 1:
                torrent_progress = file_progress[i] / f.size if f.size > 0 else 0
                if torrent_progress >= 0.99:
                    self.http_downloader.clear(filepath)

        for f in files:
            filename = os.path.basename(f.path)

            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
            output_filepath = _get_output_filepath(magnet_hash, filepath)

            if is_state(filename, FileStatus.DOWNLOAD_FINISHED):
                if not os.path.isfile(filepath):
                    log.debug(f"File not found, skipping: {filepath}")
                    continue
                subtitle_filenames = _subtitle_filenames(h, filepath)
                available_subtitle_languages = [lang for lang in [get_subtitle_language(fn) for fn in subtitle_filenames] if lang]
                embedded_subtitle_languages = [lang for (_, lang) in video_conversion.get_sub_tracks(filepath)]
                self._download_external_subtitles(filepath, skip=available_subtitle_languages + embedded_subtitle_languages)
            elif is_state(filename, FileStatus.WAITING_FOR_CONVERSION):
                if not os.path.isfile(filepath):
                    log.debug(f"File not found for conversion, skipping: {filepath}")
                    continue
                self.http_downloader.clear(filepath)
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                self.video_converter.convert_file(filepath, output_filepath)
            elif is_state(filename, FileStatus.READY_TO_COPY) or is_state(
                filename, FileStatus.CONVERSION_FAILED
            ):
                if not os.path.isfile(filepath):
                    log.debug(f"File not found for copy, skipping: {filepath}")
                    continue
                output_dir = os.path.dirname(output_filepath)
                os.makedirs(output_dir, exist_ok=True)
                shutil.copy(filepath, output_filepath)

    @log.catch_and_log_exceptions
    def _heartbeat(self) -> None:
        # Process libtorrent session alerts for better monitoring
        self.torrent_client.process_alerts()

        # Fail over to libtorrent when an HTTP download errored: restore the
        # file's priority on libtorrent's handle and drop it from
        # `_http_served` so peers can finish the download. Keep the failure
        # entry only if it matched an `_http_served` row whose recovery raised
        # — that's the case worth retrying. Recovered, or orphaned (no
        # matching row, or the torrent is already gone), → discard.
        for failed_path in list(self.http_downloader.failures):
            matched = False
            recovery_failed = False
            for mh, names in list(self._http_served.items()):
                for fn in list(names):
                    if _get_download_path(mh, fn) != failed_path:
                        continue
                    matched = True
                    h = self.torrent_client.torrents.get(mh)
                    if h is None:
                        names.discard(fn)
                        continue
                    try:
                        with self.torrent_client.locks.lock(mh):
                            i, _ = torrent.get_index_and_file_from_files(h, fn)
                            if i is not None:
                                priorities = list(h.file_priorities())
                                priorities[i] = 4
                                torrent.prioritize_files(h, priorities)
                        names.discard(fn)
                    except Exception:
                        log.write_log()
                        recovery_failed = True
                if not names:
                    self._http_served.pop(mh, None)
            if not (matched and recovery_failed):
                self.http_downloader.failures.discard(failed_path)

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
                    self._http_served.pop(magnet_hash, None)
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
        if not self._stop_event.is_set():
            print("FATAL: Daemon thread exited unexpectedly", flush=True)
            os._exit(1)

    def _loop(self) -> None:
        while not self._stop_event.wait(timeout=1):
            self._heartbeat()
