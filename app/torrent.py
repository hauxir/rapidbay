import urllib
import json
import os
import shutil
import time
import random
import sys
import hashlib
import base64

import bencodepy
import libtorrent

from locking import LockManager


def get_torrent_info(h):
    while not h.has_metadata():
        time.sleep(1)
    return h.get_torrent_info()


def get_index_and_file_from_files(h, filename):
    """
    Get the index and file object of a file in a torrent.

    :param h: The handle
    to the torrent.
    :type h: libtorrent.torrent_handle
    :param filename: The
    name of the file to find in the torrent's files list.
    """
    files = list(get_torrent_info(h).files())
    try:
        return next((i, f) for (i, f) in enumerate(files) if f.path.endswith(filename))
    except StopIteration:
        return (None, None)


def make_magnet_from_torrent_file(file):
    """
    Given a file containing the contents of a torrent file, return the magnet
    link for that torrent.

    :param str file: The path to the .torrent file.
    :returns: A magnet link for that .torrent.
    """
    metadata = bencodepy.decode_from_file(file)
    subj = metadata.get(b"info", {})
    hashcontents = bencodepy.encode(subj)
    digest = hashlib.sha1(hashcontents).digest()
    b16hash = base64.b16encode(digest).decode().lower()
    return (
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
                for tr in trlist
                if tr.decode().strip()
            ]
        )
        + "&xl="
        + str(metadata.get(b"info", {}).get(b"length"))
    )


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
    """
    Given a magnet link, return the hash of the torrent.

    :param str
    magnet_link: The magnet link to parse.
    :returns str: The hash of the
    torrent file.
    """
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
        self,
        listening_port=None,
        dht_routers=[],
        filelist_dir=None,
        download_dir=None,
        torrents_dir=None,
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
        self.torrents_dir = torrents_dir

    def fetch_filelist_from_link(self, magnet_link):
        """
        Fetches the filelist for a given magnet link and saves it to disk.

        :param
        str magnet_link: The magnet link of the torrent.
        """
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

    def save_torrent_file(self, torrent_filepath):
        """
        Saves a torrent file to the specified directory.

        :param str
        torrent_filepath: The path to the .torrent file.
        """
        magnet_link = make_magnet_from_torrent_file(torrent_filepath)
        magnet_hash = get_hash(magnet_link)
        os.makedirs(self.torrents_dir, exist_ok=True)
        filepath = os.path.join(self.torrents_dir, f"{magnet_hash}.torrent")
        shutil.copy(torrent_filepath, filepath)

    def download_file(self, magnet_link, filename):
        """
        Downloads a file from the given magnet link.

        :param str magnet_link: The
        magnet link to download the file from.
        :param str filename: The name of the
        file to download.
        """
        magnet_hash = get_hash(magnet_link)
        with self.locks.lock(magnet_hash):
            h = (
                self.torrents.get(magnet_hash)
                or self._add_torrent_file_to_downloads(
                    os.path.join(self.torrents_dir, f"{magnet_hash}.torrent")
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
            except OSError:
                pass

    def _add_torrent_file_to_downloads(self, filepath):
        """
        Adds a torrent file to the downloads directory.

        :param str filepath: The
        path to the torrent file.
        :returns libtorrent.torrent_handle h: The handle
        of the added torrent, or None if it failed to add for some reason (e.g.,
        already exists).
        """
        if not os.path.isfile(filepath):
            return None
        magnet_link = make_magnet_from_torrent_file(filepath)
        magnet_hash = get_hash(magnet_link)
        info = libtorrent.torrent_info(filepath)
        h = self.torrents.get(magnet_hash) or self.session.add_torrent(
            dict(ti=info, save_path=os.path.join(self.download_dir, magnet_hash))
        )
        self.torrents[magnet_hash] = h
        files = get_torrent_info(h).files()
        prioritize_files(h, [0] * len(files))
        return h

    def _add_magnet_link_to_downloads(self, magnet_link):
        """
        Adds a magnet link to the download queue.

        :param str magnet_link: The
        magnet link to add.
        :returns libtorrent.handle -- A handle for the torrent
        that was added, or None if it failed to be added.

            :raises ValueError
        -- If ``magnet_link`` is not a valid URL or Magnet Link string, this
        exception will be raised with an appropriate message explaining why it
        could not be parsed as one of those two types of strings (URLs are parsed
        via :func:`urllib3.util.parse_url`).

            .. note :: This function does NOT
        check whether ``magnet_link`` is already in the download queue; if it is,
        then calling this function will simply have no effect and return None
        instead of adding another copy of that same file!  It also does NOT check
        whether there are any files in the torrent info object returned by
        :func:`get_torrent_info`, so you can pass in a handle for an existing
        torrent and this function will happily add another file from that same
        torrent (or even try adding multiple copies from different files within
        that single torrent).  You must ensure yourself before calling this
        function that all necessary checks have been
        """
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
        """
        Write a list of files contained in the torrent to disk.

        :param str
        magnet_link: The magnet link for the torrent.
        """
        magnet_hash = get_hash(magnet_link)
        filename = os.path.join(self.filelist_dir, magnet_hash)
        h = (
            self.torrents.get(magnet_hash)
            or self._add_torrent_file_to_downloads(
                os.path.join(self.torrents_dir, f"{magnet_hash}.torrent")
            )
            or self._add_magnet_link_to_downloads(magnet_link)
        )
        result = [f.path for f in get_torrent_info(h).files()]
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(json.dumps(result))
