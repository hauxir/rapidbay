from typing import List

from . import real_debrid, torbox

_providers = [real_debrid, torbox]


def get_cached_url(magnet_hash: str, filename: str) -> str | None:
    for provider in _providers:
        cached_url = provider.get_cached_url(magnet_hash, filename)
        if cached_url:
            return cached_url

    return None

def get_cached_filelist(magnet_hash: str) -> List[str] | None:
    for provider in _providers:
        filelist = provider.get_filelist(magnet_hash)
        if filelist:
            return filelist

    return None
