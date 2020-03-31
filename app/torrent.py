import json
import os
import shutil
import time
import random

import libtorrent
from locking import LockManager


def get_torrent_info(h):
    while not h.has_metadata():
        time.sleep(1)
    return h.get_torrent_info()


def get_index_and_file_from_files(h, filename):
    files = list(get_torrent_info(h).files())
    try:
        return next((i, f) for (i, f) in enumerate(files) if f.path.endswith(filename))
    except StopIteration:
        return (None, None)


def torrent_is_finished(h):
    return (
        str(h.status().state) in ["finished", "seeding"]
        or sum(h.file_priorities()) == 0
    )


def prioritize_files(h, priorities):
    h.prioritize_files(priorities)
    while h.file_priorities() != priorities:
        time.sleep(1)


def get_hash(magnet_link):
    if not magnet_link.startswith("magnet:?xt=urn:btih:"):
        raise Exception("Invalid magnet link")
    return magnet_link[
        magnet_link.find("btih:") + 5 : magnet_link.find("&")
        if "&" in magnet_link
        else len(magnet_link)
    ].lower()


class TorrentClient:
    torrents = {}

    def __init__(
        self, listening_port=None, dht_routers=[], filelist_dir=None, download_dir=None
    ):
        self.locks = LockManager()
        self.session = libtorrent.session()
        if listening_port:
            self.session.listen_on(listening_port, listening_port)
        else:
            rand = random.randrange(17000, 18000)
            self.session.listen_on(rand, rand + 10000)
        for router, port in dht_routers:
            self.session.add_dht_router(router, port)
        self.session.start_dht()
        self.filelist_dir = filelist_dir
        self.download_dir = download_dir

    def fetch_filelist_from_link(self, magnet_link):
        if self.filelist_dir is None:
            return
        magnet_hash = get_hash(magnet_link)
        filename = os.path.join(self.filelist_dir, magnet_hash)
        with self.locks.lock(magnet_hash):
            if os.path.isfile(filename):
                try:
                    with open(filename, "r") as f:
                        data = f.read().replace("\n", "")
                        json.loads(data)
                        return
                except json.decoder.JSONDecodeError:
                    os.remove(filename)
            self._write_filelist_to_disk(magnet_link)

    def download_file(self, magnet_link, filename):
        magnet_hash = get_hash(magnet_link)
        with self.locks.lock(magnet_hash):
            h = self.torrents.get(magnet_hash) or self._add_magnet_link_to_downloads(
                magnet_link
            )
            files = get_torrent_info(h).files()
            file_priorities = h.file_priorities()
            for i, f in enumerate(files):
                if f.path.endswith(filename):
                    file_priorities[i] = 4
                    break
            prioritize_files(h, file_priorities)
            self._write_filelist_to_disk(magnet_link)

    def remove_torrent(self, magnet_hash, remove_files=False):
        try:
            h = self.torrents[magnet_hash]
        except KeyError:
            return
        try:
            self.session.remove_torrent(h)
        except Exception:
            pass
        del self.torrents[magnet_hash]
        if remove_files:
            try:
                shutil.rmtree(os.path.join(self.download_dir, magnet_hash))
            except FileNotFoundError:
                pass

    def _add_magnet_link_to_downloads(self, magnet_link):
        magnet_hash = get_hash(magnet_link)
        h = libtorrent.add_magnet_uri(
            self.session,
            magnet_link,
            dict(save_path=os.path.join(self.download_dir, magnet_hash)),
        )
        files = get_torrent_info(h).files()
        prioritize_files(h, [0] * len(files))
        self.torrents[magnet_hash] = h
        return h

    def _write_filelist_to_disk(self, magnet_link):
        magnet_hash = get_hash(magnet_link)
        filename = os.path.join(self.filelist_dir, magnet_hash)
        h = self.torrents.get(magnet_hash) or self._add_magnet_link_to_downloads(
            magnet_link
        )
        result = sorted(
            [
                os.path.basename(os.path.normpath(f.path))
                for f in get_torrent_info(h).files()
            ]
        )
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(json.dumps(result))
