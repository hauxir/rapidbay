import json
import math
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

NORMAL_PRIORITY = 1
HIGHEST_PRIORITY = 7


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


def make_magnet_from_torrent_file(file):
    metadata = bencodepy.decode_from_file(file)
    subj = metadata.get(b'info', {})
    hashcontents = bencodepy.encode(subj)
    digest = hashlib.sha1(hashcontents).digest()
    b32hash = base64.b32encode(digest).decode()
    return 'magnet:?'\
             + 'xt=urn:btih:' + b32hash\
             + '&dn=' + metadata.get(b'info', {}).get(b'name', b'').decode()\
             + '&tr=' + metadata.get(b'announce', b'').decode()\
             + "".join([
                "&tr=" + tr.decode()
                for trlist in metadata.get(b'announce-list', [])
                for tr in trlist
                if tr.decode().strip()
             ])\
             + '&xl=' + str(metadata.get(b'info', {}).get(b'length'))


def torrent_is_finished(h):
    return (
        str(h.status().state) in ["finished", "seeding"]
        or sum(h.file_priorities()) == 0
    )


def prioritize_files(h, priorities):
    get_torrent_info(h)
    piece_priorities_before = list(h.piece_priorities())
    h.prioritize_files(priorities)

    while h.file_priorities() != priorities:
        time.sleep(1)

    piece_priorities_after = list(h.piece_priorities())

    for i, priority in enumerate(piece_priorities_before):
        if priority == HIGHEST_PRIORITY:
            piece_priorities_after[i] = priority

    prioritize_pieces(h, piece_priorities_after)


def prioritize_pieces(h, priorities):
    h.prioritize_pieces(priorities)
    while list(h.piece_priorities()) != priorities:
        time.sleep(1)


def get_hash(magnet_link):
    if not magnet_link.startswith("magnet:?xt=urn:btih:"):
        raise Exception("Invalid magnet link")
    return magnet_link[
        magnet_link.find("btih:") + 5 : magnet_link.find("&")
        if "&" in magnet_link
        else len(magnet_link)
    ].lower()


def get_file_piece_indexes(h, f):
    torrent_info = get_torrent_info(h)
    total_pieces = len(list(h.piece_priorities()))
    bytes_per_piece = torrent_info.piece_length()
    total_torrent_size = torrent_info.total_size()

    file_size = f.size
    file_offset = f.offset

    n_pieces = math.ceil(file_size * 1.0 / bytes_per_piece)
    piece_offset = max(math.floor(file_offset * 1.0 / bytes_per_piece), 0)

    last_piece_index = min(piece_offset + n_pieces - 1, total_pieces - 1)

    return piece_offset, last_piece_index


def prioritize_first_n_pieces(h, f, n):
    get_torrent_info(h)
    first_piece_index, _last_piece_index = get_file_piece_indexes(h, f)

    piece_priorities = list(h.piece_priorities())
    n = min(n, len(piece_priorities) - first_piece_index)

    for i in range(first_piece_index, first_piece_index + n):
        piece_priorities[i] = HIGHEST_PRIORITY
    prioritize_pieces(h, piece_priorities)


def prioritize_last_n_pieces(h, f, n):
    get_torrent_info(h)
    _first_piece_index, last_piece_index = get_file_piece_indexes(h, f)

    piece_priorities = list(h.piece_priorities())
    n = min(n, len(piece_priorities))

    for i in range((last_piece_index - n) + 1, last_piece_index + 1):
        piece_priorities[i] = HIGHEST_PRIORITY
    prioritize_pieces(h, piece_priorities)


def get_prioritized_padding(h, f):
    min_file_padding = 2000000
    return max(
        math.ceil(min_file_padding * 1.0 / get_torrent_info(h).piece_length()), 3
    )


def have_pieces(h, from_index, to_index):
    return all([h.have_piece(i) for i in range(from_index, to_index)])


def padded_pieces_completed(h, f):
    first_piece_index, last_piece_index = get_file_piece_indexes(h, f)
    prioritized_padding = get_prioritized_padding(h, f)

    have_beginning_pieces = have_pieces(
        h, first_piece_index, first_piece_index + prioritized_padding
    )

    have_end_pieces = have_pieces(
        h, last_piece_index - prioritized_padding + 1, last_piece_index + 1
    )

    return have_beginning_pieces and have_end_pieces


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
                    file_priorities[i] = NORMAL_PRIORITY
                    break
            prioritize_files(h, file_priorities)

            prioritized_padding = get_prioritized_padding(h, f)

            prioritize_first_n_pieces(h, f, prioritized_padding)
            prioritize_last_n_pieces(h, f, prioritized_padding)

            self._write_filelist_to_disk(magnet_link)

    def padded_pieces_completed(self, magnet_hash, filename):
        h = self.torrents.get(magnet_hash)
        files = get_torrent_info(h).files()
        for i, f in enumerate(files):
            if f.path.endswith(filename):
                break
        return padded_pieces_completed(h, f)

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
            dict(
                save_path=os.path.join(self.download_dir, magnet_hash),
                storage_mode=libtorrent.storage_mode_t(0),
            ),
        )
        files = get_torrent_info(h).files()
        prioritize_files(h, [0] * len(files))
        prioritize_pieces(h, [0] * len(list(h.piece_priorities())))
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
