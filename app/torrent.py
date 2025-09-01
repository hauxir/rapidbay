import base64
import contextlib
import hashlib
import json
import os
import random
import shutil
import time
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import bencodepy
import libtorrent
from locking import LockManager


def get_torrent_info(h: libtorrent.torrent_handle) -> libtorrent.torrent_info:
    while not h.has_metadata():
        time.sleep(1)
    return h.get_torrent_info()


def get_index_and_file_from_files(h: libtorrent.torrent_handle, filename: str) -> Tuple[Optional[int], Optional["libtorrent.file_entry"]]:
    files = list(get_torrent_info(h).files())
    try:
        return next((i, f) for (i, f) in enumerate(files) if f.path.endswith(filename))
    except StopIteration:
        return (None, None)


def make_magnet_from_torrent_file(file: str) -> str:
    metadata = bencodepy.decode_from_file(file)
    subj = metadata.get(b"info", {})
    hashcontents = bencodepy.encode(subj)
    digest = hashlib.sha1(hashcontents).digest()
    b16hash = base64.b16encode(digest).decode().lower()
    return str(
        "magnet:?"
        + "xt=urn:btih:"
        + b16hash
        + "&dn="
        + metadata.get(b"info", {}).get(b"name", b"").decode()
        + "&tr="
        + metadata.get(b"announce", b"").decode()
        + "".join(
            [
                "&tr=" + tr.decode()
                for trlist in metadata.get(b"announce-list", [])
                for tr in (trlist if isinstance(trlist, list) else [])  # type: ignore
                if isinstance(tr, bytes) and tr.decode().strip()
            ]
        )
        + "&xl="
        + str(metadata.get(b"info", {}).get(b"length"))
    )


def torrent_is_finished(h: libtorrent.torrent_handle) -> bool:
    return (
        str(h.status().state) in ["finished", "seeding"]
        or sum(h.file_priorities()) == 0
    )


def prioritize_files(h: libtorrent.torrent_handle, priorities: List[int]) -> None:
    h.prioritize_files(priorities)
    while h.file_priorities() != priorities:
        time.sleep(1)


def get_hash(magnet_link: str) -> str:
    if not magnet_link.startswith("magnet:?xt=urn:btih:"):
        raise Exception("Invalid magnet link")
    return magnet_link[
        magnet_link.find("btih:") + 5 : magnet_link.find("&")
        if "&" in magnet_link
        else len(magnet_link)
    ].lower()


def parse_proxy_url(proxy_url: Optional[str]) -> Optional[Dict[str, Union[libtorrent.proxy_type_t, str, int, bool]]]:
    """
    Parse proxy settings from a URL string or environment variable.
    Supports HTTP, HTTPS, SOCKS4, SOCKS5 proxy URLs.
    Format: [protocol://][username:password@]hostname:port
    
    Examples:
      socks5://127.0.0.1:1080
      http://user:pass@proxy.example.com:8080
      proxy.example.com:3128 (defaults to http)
    """
    # Use provided proxy_url or fall back to environment variable
    url = proxy_url or os.environ.get('PROXY_URL')
    if not url:
        return None

    try:
        # Parse the proxy URL
        if '://' not in url:
            # Add default protocol if missing
            if any(url.startswith(p) for p in ['socks5:', 'socks4:', 'http:', 'https:']):
                url = url.replace(':', '://', 1)
            else:
                url = 'http://' + url

        parsed = urlparse(url)

        # Determine proxy type
        proxy_type = libtorrent.proxy_type_t.none
        if parsed.scheme in ['socks5', 'socks5h']:
            if parsed.username and parsed.password:
                proxy_type = libtorrent.proxy_type_t.socks5_pw
            else:
                proxy_type = libtorrent.proxy_type_t.socks5
        elif parsed.scheme == 'socks4':
            proxy_type = libtorrent.proxy_type_t.socks4
        elif parsed.scheme in ['http', 'https']:
            if parsed.username and parsed.password:
                proxy_type = libtorrent.proxy_type_t.http_pw
            else:
                proxy_type = libtorrent.proxy_type_t.http

        if proxy_type != libtorrent.proxy_type_t.none and parsed.hostname:
            proxy_settings: Dict[str, Union[libtorrent.proxy_type_t, str, int, bool]] = {
                'proxy_type': proxy_type,
                'proxy_hostname': parsed.hostname,
                'proxy_port': parsed.port or 1080,  # Default to 1080 for SOCKS, will be overridden for HTTP
                'proxy_username': parsed.username or '',
                'proxy_password': parsed.password or '',
                'proxy_peer_connections': True,
                'proxy_tracker_connections': True,
            }

            # Set default port based on protocol if not specified
            if not parsed.port:
                if parsed.scheme in ['http', 'https']:
                    proxy_settings['proxy_port'] = 8080
                elif parsed.scheme in ['socks5', 'socks5h', 'socks4']:
                    proxy_settings['proxy_port'] = 1080

            print(f"Proxy configured: {parsed.scheme}://{parsed.hostname}:{proxy_settings['proxy_port']}")
            return proxy_settings
    except Exception as e:
        print(f"Error parsing proxy URL: {e}")

    return None


class TorrentClient:
    torrents: Dict[str, libtorrent.torrent_handle] = {}

    def __init__(
        self,
        listening_port: Optional[int] = None,
        dht_routers: Optional[List[Tuple[str, int]]] = None,
        filelist_dir: Optional[str] = None,
        download_dir: Optional[str] = None,
        torrents_dir: Optional[str] = None,
        proxy_url: Optional[str] = None,
    ) -> None:
        self.locks: LockManager = LockManager()
        if listening_port:
            listen_interfaces = f'0.0.0.0:{listening_port},[::]:{listening_port}'
        else:
            rand = random.randrange(17000, 18000)
            listen_interfaces = f'0.0.0.0:{rand},[::]:{rand}'

        # Create session parameters
        params = libtorrent.session_params()
        session_settings = params.settings
        session_settings['listen_interfaces'] = listen_interfaces

        # Apply proxy settings (explicit proxy_url takes priority over PROXY_URL env var)
        proxy_settings = parse_proxy_url(proxy_url)

        if proxy_settings:
            for key, value in proxy_settings.items():
                session_settings[key] = value

        # Update params with modified settings
        params.settings = session_settings

        # Create session with configured settings
        self.session: libtorrent.session = libtorrent.session(params)

        for router, port in dht_routers or []:
            self.session.add_dht_node((router, port))
        self.session.start_dht()
        self.filelist_dir: Optional[str] = filelist_dir
        self.download_dir: Optional[str] = download_dir
        self.torrents_dir: Optional[str] = torrents_dir

    def fetch_filelist_from_link(self, magnet_link: str) -> None:
        if self.filelist_dir is None:
            return
        magnet_hash = get_hash(magnet_link)
        filename = os.path.join(self.filelist_dir, magnet_hash)
        with self.locks.lock(magnet_hash):
            if os.path.isfile(filename):
                try:
                    with open(filename) as f:
                        data = f.read().replace("\n", "")
                        json.loads(data)
                        return
                except json.decoder.JSONDecodeError:
                    os.remove(filename)
            self._write_filelist_to_disk(magnet_link)

    def save_torrent_file(self, torrent_filepath: str) -> None:
        magnet_link = make_magnet_from_torrent_file(torrent_filepath)
        magnet_hash = get_hash(magnet_link)
        os.makedirs(self.torrents_dir, exist_ok=True)  # type: ignore
        filepath = os.path.join(self.torrents_dir, f"{magnet_hash}.torrent")  # type: ignore
        shutil.copy(torrent_filepath, filepath)

    def download_file(self, magnet_link: str, filename: str) -> None:
        magnet_hash = get_hash(magnet_link)
        with self.locks.lock(magnet_hash):
            h = (
                self.torrents.get(magnet_hash)
                or self._add_torrent_file_to_downloads(
                    os.path.join(self.torrents_dir, f"{magnet_hash}.torrent")  # type: ignore
                )
                or self._add_magnet_link_to_downloads(magnet_link)
            )
            files = get_torrent_info(h).files()
            file_priorities = h.file_priorities()
            for i, f in enumerate(files):
                if f.path.endswith(filename):
                    file_priorities[i] = 4
                    break
            prioritize_files(h, file_priorities)
            self._write_filelist_to_disk(magnet_link)

    def remove_torrent(self, magnet_hash: str, remove_files: bool = False) -> None:
        try:
            h = self.torrents[magnet_hash]
        except KeyError:
            return
        with contextlib.suppress(Exception):
            self.session.remove_torrent(h)
        del self.torrents[magnet_hash]
        if remove_files:
            try:
                shutil.rmtree(os.path.join(self.download_dir, magnet_hash))  # type: ignore
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def _add_torrent_file_to_downloads(self, filepath: str) -> Optional[libtorrent.torrent_handle]:
        if not os.path.isfile(filepath):
            return None
        magnet_link = make_magnet_from_torrent_file(filepath)
        magnet_hash = get_hash(magnet_link)
        info: libtorrent.torrent_info = libtorrent.torrent_info(filepath)
        h: libtorrent.torrent_handle = self.torrents.get(magnet_hash) or self.session.add_torrent(
            {"ti": info, "save_path": os.path.join(self.download_dir, magnet_hash)}  # type: ignore
        )
        self.torrents[magnet_hash] = h
        files = get_torrent_info(h).files()
        prioritize_files(h, [0] * len(files))
        return h

    def _add_magnet_link_to_downloads(self, magnet_link: str) -> libtorrent.torrent_handle:
        magnet_hash = get_hash(magnet_link)
        h: libtorrent.torrent_handle = libtorrent.add_magnet_uri(
            self.session,
            magnet_link,
            {"save_path": os.path.join(self.download_dir, magnet_hash)},  # type: ignore
        )
        files = get_torrent_info(h).files()
        prioritize_files(h, [0] * len(files))
        self.torrents[magnet_hash] = h
        return h

    def _write_filelist_to_disk(self, magnet_link: str) -> None:
        magnet_hash = get_hash(magnet_link)
        filename = os.path.join(self.filelist_dir, magnet_hash)  # type: ignore
        h = (
            self.torrents.get(magnet_hash)
            or self._add_torrent_file_to_downloads(
                os.path.join(self.torrents_dir, f"{magnet_hash}.torrent")  # type: ignore
            )
            or self._add_magnet_link_to_downloads(magnet_link)
        )
        result = [f.path for f in get_torrent_info(h).files()]
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(json.dumps(result))
