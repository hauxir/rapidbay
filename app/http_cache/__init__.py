from typing import Optional

from . import real_debrid


def get_cached_url(magnet_hash: str, filename: str) -> Optional[str]:
    rd_cached_url = real_debrid.get_cached_url(magnet_hash, filename)

    if rd_cached_url:
        return rd_cached_url

    return None
