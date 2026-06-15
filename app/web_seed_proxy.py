import http.server
import os
import threading
from typing import Dict, Optional, Tuple, override
from urllib.parse import unquote

import http_cache
import log
import requests
from common import normalize_filename

# Localhost TCP endpoint that libtorrent connects to when web-seeding a debrid
# (Real-Debrid / TorBox) file. libtorrent builds a GetRight (BEP19) URL by
# appending the in-torrent file path to a base URL, but debrid hands out opaque
# per-file URLs that can't be addressed that way — so we point the web seed at
# this shim and map each requested in-torrent path back to its debrid URL.
#
# The shim is a *reverse proxy*: it fetches the debrid bytes itself via requests
# (which honors HTTP_PROXY/HTTPS_PROXY → tinyproxy) and streams them to
# libtorrent over localhost. So the bulk download leaves the box through the
# same tinyproxy path — and therefore the same IP — as the debrid API calls,
# rather than out the VPN. libtorrent stays the sole writer and hash-verifies
# every piece, falling back to peers on its own if the shim can't serve.
HOST = "127.0.0.1"
PORT = int(os.environ.get("WEB_SEED_PROXY_PORT", "18889"))
_CHUNK = 1 << 16
_CONNECT_TIMEOUT = 15
_READ_TIMEOUT = 30
# Statuses that mean the debrid link is gone/expired and worth re-resolving.
_STALE_STATUSES = {401, 403, 404, 410}

_lock = threading.Lock()
# (provider, magnet_hash) -> { normalized basename -> (filename, debrid url) }
# Keyed per provider so Real-Debrid and TorBox can be attached as two separate
# web seeds for the same torrent and each resolve to its own debrid URL.
_registry: Dict[Tuple[str, str], Dict[str, Tuple[str, str]]] = {}
_server: Optional["http.server.ThreadingHTTPServer"] = None


def register(provider: str, magnet_hash: str, filename: str, url: str) -> None:
    with _lock:
        _registry.setdefault((provider, magnet_hash), {})[
            normalize_filename(os.path.basename(filename))
        ] = (filename, url)


def unregister(magnet_hash: str) -> None:
    with _lock:
        for key in [k for k in _registry if k[1] == magnet_hash]:
            _registry.pop(key, None)


def _lookup(
    provider: str, magnet_hash: str, request_path: str
) -> Tuple[str, str] | None:
    key = normalize_filename(os.path.basename(unquote(request_path)))
    with _lock:
        return _registry.get((provider, magnet_hash), {}).get(key)


def _open(url: str, range_header: str | None) -> requests.Response | None:
    headers = {"Range": range_header} if range_header else {}
    try:
        return requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
    except Exception as e:
        log.debug(f"web seed proxy: upstream fetch failed: {e}")
        return None


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _serve(self, write_body: bool) -> None:
        # path is /{provider}/{magnet_hash}/{in-torrent file path...}
        parts = self.path.lstrip("/").split("/", 2)
        if len(parts) != 3:
            self._fail(404)
            return
        provider, magnet_hash, rest = parts
        entry = _lookup(provider, magnet_hash, rest)
        if entry is None:
            self._fail(404)
            return

        filename, url = entry
        range_header = self.headers.get("Range")
        resp = _open(url, range_header)

        # Link likely expired — re-resolve once (from the same provider) and retry.
        if resp is not None and resp.status_code in _STALE_STATUSES:
            resp.close()
            fresh = http_cache.get_provider_url(provider, magnet_hash, filename)
            if fresh and fresh != url:
                register(provider, magnet_hash, filename, fresh)
                resp = _open(fresh, range_header)

        if resp is None:
            self._fail(502)
            return

        try:
            self._relay(resp, write_body)
        finally:
            resp.close()

    def _relay(self, resp: requests.Response, write_body: bool) -> None:
        self.send_response(resp.status_code)
        content_length = resp.headers.get("Content-Length")
        for header in ("Content-Range", "Content-Type"):
            value = resp.headers.get(header)
            if value:
                self.send_header(header, value)
        self.send_header("Accept-Ranges", "bytes")
        if content_length is not None:
            self.send_header("Content-Length", content_length)
        else:
            # Unknown length — can't keep the connection alive safely.
            self.send_header("Connection", "close")
        self.end_headers()

        if not write_body:
            return
        try:
            for chunk in resp.iter_content(_CHUNK):
                if chunk:
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # libtorrent closed the connection once it had the bytes it wanted.
            pass

    def _fail(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        self._serve(write_body=True)

    def do_HEAD(self) -> None:
        self._serve(write_body=False)

    @override
    def log_message(self, format: str, *args: object) -> None:
        pass


def start() -> None:
    global _server
    with _lock:
        if _server is not None:
            return
        http.server.ThreadingHTTPServer.allow_reuse_address = True
        _server = http.server.ThreadingHTTPServer((HOST, PORT), _Handler)
        threading.Thread(target=_server.serve_forever, daemon=True).start()
        log.debug(f"web seed proxy listening on {HOST}:{PORT}")


def base_url(provider: str, magnet_hash: str) -> str:
    """Directory-form GetRight web seed base. libtorrent appends the torrent
    name and file path, yielding /{provider}/{magnet_hash}/{name}/{path}. The
    provider segment makes each debrid backend a distinct web seed URL so
    libtorrent fans piece requests out across them in parallel."""
    start()
    return f"http://{HOST}:{PORT}/{provider}/{magnet_hash}/"
