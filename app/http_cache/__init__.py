from typing import List

from . import real_debrid


def get_cached_url(magnet_hash: str, filename: str) -> str | None:
    rd_cached_url = real_debrid.get_cached_url(magnet_hash, filename)

    if rd_cached_url:
        return rd_cached_url

    return None

def get_cached_filelist(magnet_hash: str) -> List[str] | None:
    return real_debrid.get_filelist(magnet_hash)
