import base64
import contextlib
import hashlib
import json
import os
import random
import shutil
import time
from typing import Dict, List, Optional, Tuple

import bencodepy
import libtorrent
from locking import LockManager


def get_torrent_info(h: libtorrent.torrent_handle) -> libtorrent.torrent_info:
    while not h.has_metadata():
        time.sleep(1)
    return h.get_torrent_info()


def get_index_and_file_from_files(h: libtorrent.torrent_handle, filename: str) -> Tuple[Optional[int], Optional[libtorrent.file_entry]]:
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


class TorrentClient:
    torrents: Dict[str, libtorrent.torrent_handle] = {}

    def __init__(
        self,
        listening_port: Optional[int] = None,
        dht_routers: Optional[List[Tuple[str, int]]] = None,
        filelist_dir: Optional[str] = None,
        download_dir: Optional[str] = None,
        torrents_dir: Optional[str] = None,
    ) -> None:
        self.locks: LockManager = LockManager()
        self.session: libtorrent.session = libtorrent.session()
        settings = self.session.get_settings()
        if listening_port:
            settings['listen_interfaces'] = f'0.0.0.0:{listening_port},[::1]:{listening_port}'
        else:
            rand = random.randrange(17000, 18000)
            settings['listen_interfaces'] = f'0.0.0.0:{rand},[::1]:{rand}'
        self.session.apply_settings(settings)
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
