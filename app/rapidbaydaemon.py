import contextlib
import datetime
import json
import os
import shutil
import subprocess
import time
from threading import Event, Lock, Thread
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


def _get_output_dir(magnet_hash: str) -> str:
    return os.path.join(settings.OUTPUT_DIR, magnet_hash)


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


def _m3u8_filename(video_filename: str) -> str:
    return os.path.splitext(os.path.basename(video_filename))[0] + ".m3u8"


def _m3u8_path(magnet_hash: str, video_filename: str) -> str:
    return os.path.join(_get_output_dir(magnet_hash), _m3u8_filename(video_filename))


def _is_safe_subpath(parent: str, child: str) -> bool:
    """True iff `child` resolves to a path inside `parent` (no traversal)."""
    try:
        parent_abs = os.path.realpath(parent)
        child_abs = os.path.realpath(child)
    except (OSError, ValueError):
        return False
    return os.path.commonpath([parent_abs, child_abs]) == parent_abs


def _hls_effective_threshold(file_size: int) -> int:
    # Cap the configured threshold at a fraction of the file size so small
    # files (e.g. 30 MB) aren't permanently locked out of HLS by a 50 MB floor.
    # Floor at 1 MiB so very tiny files still see a meaningful warm-up window.
    return min(settings.HLS_START_THRESHOLD, max(file_size // 4, 1024 * 1024))


def _get_vtt_subtitles(output_dir: str) -> List[str]:
    if not os.path.isdir(output_dir):
        return []
    return sorted(
        [f for f in os.listdir(output_dir) if f.endswith(".vtt") and "_" in os.path.splitext(f)[0]],
        key=lambda fn: fn.split("_")[-1],
    )


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
        self.hls_streamer: video_conversion.HLSStreamer = video_conversion.HLSStreamer()
        # Files we're fetching via HTTP (Real-Debrid). Tracked separately from
        # libtorrent's `file_priorities`, because we set those files to
        # priority 0 to keep libtorrent from writing the same path in parallel
        # — the daemon's lifecycle code uses `priority != 0` as a proxy for
        # "user-selected", which would otherwise drop these files from
        # `active_filenames` and remove the torrent (with files) mid-download.
        self._http_served: Dict[str, Set[str]] = {}
        self._subtitle_gate: Lock = Lock()
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

        # Add to libtorrent first so the on-disk filelist is rewritten with
        # libtorrent's view of file paths before we compute the HTTP target.
        # An RD-supplied filelist can list a file as `inner.mkv` while
        # libtorrent stores it at `<torrent_name>/inner.mkv` for multi-file
        # torrents. If the HTTP download key was computed from the RD view
        # but get_file_status later resolves the path against libtorrent's
        # view, the http_progress lookup misses and the file stalls in
        # DOWNLOADING — libtorrent's own progress is pinned at 0 once we
        # set this file's priority to 0 below.
        self.torrent_client.download_file(magnet_link, filename)

        h = self.torrent_client.torrents.get(magnet_hash)
        h.set_download_limit(settings.TORRENT_DOWNLOAD_LIMIT)  # type: ignore
        h.set_upload_limit(settings.TORRENT_UPLOAD_LIMIT)  # type: ignore

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
        is_video = filename_extension[1:] in settings.VIDEO_EXTENSIONS
        output_dir = _get_output_dir(magnet_hash)
        output_filepath = _get_output_filepath(magnet_hash, filename)
        output_extension = os.path.splitext(output_filepath)[1]

        # Determine if HLS stream is available for early playback
        hls_info: Dict[str, Any] = {}
        if is_video and settings.HLS_STREAMING:
            m3u8 = _m3u8_path(magnet_hash, filename)
            if os.path.isfile(m3u8):
                vtt_subtitles = _get_vtt_subtitles(output_dir)
                # Wrap the media playlist in a master playlist that exposes any
                # available VTTs as EXT-X-MEDIA:TYPE=SUBTITLES tracks. hls.js
                # will only render <track>-style subtitles when they're declared
                # in the manifest; serving a bare media playlist breaks subtitle
                # rendering even when text tracks exist on the <video> element.
                try:
                    master_filename = video_conversion.write_hls_master_playlist(
                        output_dir, _m3u8_filename(filename), vtt_subtitles
                    )
                except OSError:
                    master_filename = _m3u8_filename(filename)
                hls_info = {
                    'hls_filename': master_filename,
                    'hls_subtitles': vtt_subtitles,
                }
            elif m3u8 in self.hls_streamer.active_streams:
                # Stream is starting but m3u8 not written yet
                hls_info = {'hls_pending': True}
            elif not self.hls_streamer.is_failed(m3u8):
                # Check if enough data to start streaming
                ext = os.path.splitext(filename)[1].lower()
                can_pipe = ext in video_conversion.PIPE_FRIENDLY_EXTENSIONS
                if can_pipe and self._hls_can_stream(magnet_hash, filename):
                    hls_info = {'can_stream': True}

        # Check if MP4 output file exists (READY - primary output)
        if os.path.isfile(output_filepath):
            if self.video_converter.file_conversions.get(output_filepath):
                return {'status': FileStatus.FINISHING_UP, **hls_info}
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
                'supported': any(filename.endswith(ext) for ext in settings.SUPPORTED_EXTENSIONS),
                **hls_info,
            }

        # Check if MP4 conversion is in progress
        if os.path.isfile(
            f"{output_filepath}{settings.INCOMPLETE_POSTFIX}{output_extension}"
        ):
            progress = video_conversion.get_conversion_progress(output_filepath)
            if not self.video_converter.file_conversions.get(output_filepath):
                return {'status': FileStatus.CONVERSION_FAILED, **hls_info}
            return {'status': FileStatus.CONVERTING, 'progress': progress, **hls_info}

        # Torrent-based states
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h:
            return {'status': FileStatus.WAITING_FOR_TORRENT, **hls_info}
        if not h.has_metadata():
            return {'status': FileStatus.WAITING_FOR_METADATA, **hls_info}
        files = list(h.get_torrent_info().files())
        i, f = torrent.get_index_and_file_from_files(h, filename)
        if f is None or i is None:
            return {'status': FileStatus.FILE_NOT_FOUND, **hls_info}
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
                    return {'status': FileStatus.DOWNLOADING_SUBTITLES_FROM_TORRENT, **hls_info}
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                subtitle_download_status = self.subtitle_downloads.get(filepath)
                if subtitle_download_status == SubtitleDownloadStatus.DOWNLOADING:
                    return {'status': FileStatus.DOWNLOADING_SUBTITLES, **hls_info}
                if subtitle_download_status == SubtitleDownloadStatus.FINISHED:
                    return {'status': FileStatus.WAITING_FOR_CONVERSION, **hls_info}
            else:
                return {'status': FileStatus.READY_TO_COPY, **hls_info}
            return {'status': FileStatus.DOWNLOAD_FINISHED, **hls_info}
        return {
            'status': FileStatus.DOWNLOADING,
            'progress': download_progress,
            'peers': h.status().num_peers,
            **hls_info,
        }

    def start_hls_stream(self, magnet_hash: str, filename: str) -> Dict[str, Any]:
        """Start HLS streaming for a file.

        Returns a dict with:
          - started: bool — True iff a stream is now active for this file
          - reason: str (only when started=False) — one of disabled,
            unsupported_format, invalid_path, no_torrent, file_not_found,
            not_ready, capacity, codec_failed
        """
        if not settings.HLS_STREAMING:
            return {"started": False, "reason": "disabled"}
        ext = os.path.splitext(filename)[1].lower()
        if ext not in video_conversion.PIPE_FRIENDLY_EXTENSIONS:
            return {"started": False, "reason": "unsupported_format"}
        output_dir = _get_output_dir(magnet_hash)
        m3u8 = _m3u8_path(magnet_hash, filename)
        # Path-traversal guard: filename comes from URL; reject if the
        # constructed m3u8 path escapes the magnet-hash output dir.
        if not _is_safe_subpath(_get_output_dir(magnet_hash), m3u8):
            return {"started": False, "reason": "invalid_path"}
        if os.path.isfile(m3u8) or m3u8 in self.hls_streamer.active_streams:
            return {"started": True}  # Already streaming or complete
        if self.hls_streamer.is_failed(m3u8):
            return {"started": False, "reason": "codec_failed"}
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h or not h.has_metadata():
            return {"started": False, "reason": "no_torrent"}
        i, f = torrent.get_index_and_file_from_files(h, filename)
        if i is None or f is None:
            return {"started": False, "reason": "file_not_found"}
        download_root = os.path.join(settings.DOWNLOAD_DIR, magnet_hash)
        filepath = os.path.join(download_root, f.path)
        # Same guard for the input filepath — defense against pathological
        # libtorrent file paths (libtorrent normalizes, but be paranoid).
        if not _is_safe_subpath(download_root, filepath):
            return {"started": False, "reason": "invalid_path"}
        available_bytes = self._get_available_bytes(magnet_hash, filename)
        if available_bytes < _hls_effective_threshold(f.size):
            return {"started": False, "reason": "not_ready"}
        os.makedirs(output_dir, exist_ok=True)
        started = self.hls_streamer.start_stream(
            filepath,
            output_dir,
            lambda _mh=magnet_hash, _fn=filename: self._get_available_bytes(_mh, _fn),
            total_file_size=f.size,
            m3u8_filename=_m3u8_filename(filename),
        )
        return {"started": True} if started else {"started": False, "reason": "capacity"}

    def _hls_can_stream(self, magnet_hash: str, filename: str) -> bool:
        h = self.torrent_client.torrents.get(magnet_hash)
        if not h or not h.has_metadata():
            return False
        i, f = torrent.get_index_and_file_from_files(h, filename)
        if i is None or f is None:
            return False
        return self._get_available_bytes(magnet_hash, filename) >= _hls_effective_threshold(f.size)

    def _get_available_bytes(self, magnet_hash: str, filename: str) -> int:
        """Get contiguous bytes available from start of file for pipe feeding."""
        best = 0
        # Piece-based sequential bytes — only counts verified contiguous pieces from file start
        best = max(best, self.torrent_client.get_sequential_bytes(magnet_hash, filename))
        # HTTP download progress — HTTP writes sequentially to file, so this is truly sequential
        h = self.torrent_client.torrents.get(magnet_hash)
        if h and h.has_metadata():
            i, f = torrent.get_index_and_file_from_files(h, filename)
            if i is not None and f is not None:
                download_path = _get_download_path(magnet_hash, filename)
                if download_path:
                    http_progress = self.http_downloader.downloads.get(download_path, 0)
                    if http_progress > 0:
                        best = max(best, int(http_progress * f.size))
        return best

    def _download_external_subtitles(self, filepath: str, output_dir: str, skip: List[str] | None = None) -> None:
        # Test-and-set the dedup marker synchronously so racing callers (heartbeats
        # spawning while a prior download is in flight) can't both pass the check
        # and trigger duplicate OpenSubtitles fetches.
        with self._subtitle_gate:
            if self.subtitle_downloads.get(filepath):
                return
            self.subtitle_downloads[filepath] = SubtitleDownloadStatus.DOWNLOADING
        self._run_subtitle_download(filepath, output_dir, skip or [])

    @threaded
    @log.catch_and_log_exceptions
    def _run_subtitle_download(self, filepath: str, output_dir: str, skip: List[str]) -> None:
        subtitles.download_all_subtitles(filepath, skip=skip)
        # Copy downloaded .srt files to output dir as .vtt for HLS playback
        dirname = os.path.dirname(filepath)
        basename = os.path.basename(filepath)
        basename_without_ext = os.path.splitext(basename)[0]
        for srt_file in os.listdir(dirname):
            if srt_file.endswith(".srt") and srt_file.startswith(basename_without_ext):
                srt_path = os.path.join(dirname, srt_file)
                srt_stem = os.path.splitext(srt_file)[0]
                # Strip both . and _ separators so "Movie_en.srt" doesn't end up
                # as "Movie__en.vtt" (subtitles.download_all_subtitles uses both
                # styles depending on provider).
                lang = srt_stem[len(basename_without_ext):].lstrip("._")
                vtt_name = f"{basename_without_ext}_{lang}.vtt" if lang else srt_stem + ".vtt"
                vtt_path = os.path.join(output_dir, vtt_name)
                if not os.path.isfile(vtt_path):
                    # Bound runtime so a malformed SRT can't wedge the
                    # subtitle-download thread indefinitely.
                    try:
                        subprocess.run(
                            ["ffmpeg", "-nostdin", "-v", "quiet", "-i", srt_path, vtt_path],
                            check=False,
                            timeout=60,
                        )
                    except subprocess.TimeoutExpired:
                        log.debug(f"ffmpeg SRT→VTT timed out for {srt_path}")
                        with contextlib.suppress(OSError):
                            os.remove(vtt_path)
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
            output_dir = _get_output_dir(magnet_hash)
            # Defensive: HLS streams should have completed naturally by the time
            # all files are READY, but kill any stragglers before remove_files=True
            # yanks the input out from under them.
            self.hls_streamer.stop_under(output_dir)
            self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
            self._http_served.pop(magnet_hash, None)
            for f in files:
                filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                self.subtitle_downloads.pop(filepath, None)
                self.http_downloader.clear(filepath)
                m3u8 = _m3u8_path(magnet_hash, os.path.basename(f.path))
                self.hls_streamer.clear_failed(m3u8)
            video_conversion.clear_master_playlist_cache_under(output_dir)
            # Leave completed HLS artifacts (segments, playlists) on disk:
            # viewers may still be streaming from them. They'll age out via
            # _remove_old_files_and_directories like any other output file.
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

        output_dir = _get_output_dir(magnet_hash)

        for f in files:
            filename = os.path.basename(f.path)
            filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
            output_filepath = _get_output_filepath(magnet_hash, filepath)

            # MP4 conversion pipeline
            if is_state(filename, FileStatus.DOWNLOAD_FINISHED):
                if not os.path.isfile(filepath):
                    log.debug(f"File not found, skipping: {filepath}")
                    continue
                subtitle_filenames = _subtitle_filenames(h, filepath)
                available_subtitle_languages = [lang for lang in [get_subtitle_language(fn) for fn in subtitle_filenames] if lang]
                embedded_subtitle_languages = [lang for (_, lang) in video_conversion.get_sub_tracks(filepath)]
                self._download_external_subtitles(filepath, output_dir, skip=available_subtitle_languages + embedded_subtitle_languages)
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
                output_file_dir = os.path.dirname(output_filepath)
                os.makedirs(output_file_dir, exist_ok=True)
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
                    output_dir = _get_output_dir(magnet_hash)
                    # Kill any active HLS stream first; otherwise its ffmpeg +
                    # pipe-feeder threads outlive remove_files=True and spin
                    # forever waiting on bytes that will never arrive.
                    self.hls_streamer.stop_under(output_dir)
                    # Clear any HTTP downloads for this torrent before removing
                    for f in torrent.get_torrent_info(h).files():
                        filepath = os.path.join(settings.DOWNLOAD_DIR, magnet_hash, f.path)
                        self.subtitle_downloads.pop(filepath, None)
                        self.http_downloader.clear(filepath)
                    self._http_served.pop(magnet_hash, None)
                    self.torrent_client.remove_torrent(magnet_hash, remove_files=True)
                    video_conversion.clear_master_playlist_cache_under(output_dir)
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
