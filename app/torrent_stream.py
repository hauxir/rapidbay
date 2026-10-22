"""Loopback HTTP server that serves files of in-progress torrents by byte range.

ffmpeg opens torrent files through this server instead of reading the sparse
file on disk directly. Every read waits until the pieces under it are verified,
and pulls them to the front of the download with piece deadlines, so ffmpeg can
seek anywhere in a file that is still downloading: to the MKV Cues or a
trailing MP4 moov when it opens the file, and to the playhead when a viewer
skips ahead.

Rushing follows a "critical phase": right after a read starts (open, seek) only
a small window ahead of it is rushed, so nothing competes with the bytes ffmpeg
is blocked on. The window doubles each time the reader consumes half of it, up
to the read-ahead size for the file's bitrate.
"""

import contextlib
import re
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Tuple, override

import log
import settings

CRITICAL_WINDOW_BYTES = 2 * 1024 * 1024
READ_CHUNK = 256 * 1024
_WAIT_POLL = 0.05
# Re-issue deadlines this often while a read is blocked: libtorrent drops
# deadlines it can't meet (piece timeouts), and another reader on the same
# torrent may have cleared them.
_RERUSH_INTERVAL = 5.0

_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")

# (path on disk, file size) for a torrent file, or None when unknown.
Locate = Callable[[str, str], Tuple[str, int] | None]
RangeCheck = Callable[[str, str, int, int], bool]
Rush = Callable[[str, str, int, int], None]
WindowFor = Callable[[str, str], int]


def parse_range(header: str | None, size: int) -> Tuple[int, int] | None:
    """Inclusive (start, end) for a single-range `Range` header; the whole
    file when there is no header. None when the range is unsatisfiable."""
    if size <= 0:
        return None
    if not header:
        return 0, size - 1
    m = _RANGE.match(header.strip())
    if not m or (not m.group(1) and not m.group(2)):
        return None
    if not m.group(1):
        # Suffix range: the last N bytes.
        length = int(m.group(2))
        if length == 0:
            return None
        return max(0, size - length), size - 1
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else size - 1
    if start >= size or end < start:
        return None
    return start, min(end, size - 1)


class TorrentFileServer:
    def __init__(
        self,
        locate: Locate,
        is_range_downloaded: RangeCheck,
        rush: Rush,
        window_for: WindowFor,
    ) -> None:
        self._locate = locate
        self._is_range_downloaded = is_range_downloaded
        self._rush = rush
        self._window_for = window_for
        # Random path prefix: the server only listens on loopback, but other
        # local users/processes shouldn't be able to pull torrent data from it.
        self._token = secrets.token_urlsafe(16)
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self) -> None:  # noqa: N802
                server.handle(self, send_body=False)

            def do_GET(self) -> None:  # noqa: N802
                server.handle(self, send_body=True)

            @override
            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                pass

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self.port: int = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()

    def url(self, magnet_hash: str, filename: str) -> str:
        return f"http://127.0.0.1:{self.port}/{self._token}/{magnet_hash}/{urllib.parse.quote(filename)}"

    def handle(self, req: BaseHTTPRequestHandler, send_body: bool) -> None:
        parts = req.path.split("/", 3)
        if len(parts) != 4 or parts[1] != self._token:
            req.send_error(404)
            return
        magnet_hash, filename = parts[2], urllib.parse.unquote(parts[3])
        located = self._locate(magnet_hash, filename)
        if located is None:
            req.send_error(404)
            return
        path, size = located
        byte_range = parse_range(req.headers.get("Range"), size)
        if byte_range is None:
            req.send_response(416)
            req.send_header("Content-Range", f"bytes */{size}")
            req.end_headers()
            return
        start, end = byte_range
        req.send_response(206 if req.headers.get("Range") else 200)
        req.send_header("Accept-Ranges", "bytes")
        req.send_header("Content-Type", "application/octet-stream")
        req.send_header("Content-Length", str(end - start + 1))
        if req.headers.get("Range"):
            req.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        req.end_headers()
        if not send_body:
            return
        # The reader going away mid-response (ffmpeg seeked or exited) is normal.
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self._stream(req, magnet_hash, filename, path, start, end)

    def _stream(
        self,
        req: BaseHTTPRequestHandler,
        magnet_hash: str,
        filename: str,
        path: str,
        start: int,
        end: int,
    ) -> None:
        pos = start
        # Size of the last rush; nothing is rushed yet.
        window = CRITICAL_WINDOW_BYTES
        rushed_to = start
        f = None
        try:
            while pos <= end:
                if pos >= rushed_to - window // 2:
                    if rushed_to > start:
                        # Half of the last window has been read: grow it.
                        window = min(window * 2, max(CRITICAL_WINDOW_BYTES, self._window_for(magnet_hash, filename)))
                    self._rush(magnet_hash, filename, pos, pos + window)
                    rushed_to = pos + window
                chunk_end = min(end + 1, pos + READ_CHUNK)
                if not self._wait_for(magnet_hash, filename, pos, chunk_end):
                    log.debug(f"torrent_stream: gave up waiting for {filename} @ {pos}")
                    return
                if f is None:
                    f = open(path, "rb")  # noqa: SIM115
                f.seek(pos)
                data = f.read(chunk_end - pos)
                if not data:
                    return
                req.wfile.write(data)
                pos += len(data)
        finally:
            if f is not None:
                f.close()

    def _wait_for(self, magnet_hash: str, filename: str, start: int, end: int) -> bool:
        began = time.monotonic()
        last_rush = began
        while True:
            if self._is_range_downloaded(magnet_hash, filename, start, end):
                return True
            now = time.monotonic()
            if now - began > settings.HLS_STALL_TIMEOUT:
                return False
            if now - last_rush > _RERUSH_INTERVAL:
                self._rush(magnet_hash, filename, start, start + CRITICAL_WINDOW_BYTES)
                last_rush = now
            time.sleep(_WAIT_POLL)
