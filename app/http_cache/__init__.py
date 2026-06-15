from typing import List

from . import real_debrid, torbox

# TorBox first: Real Debrid DMCA-blocks (HTTP 451) most popular content, so it
# answers far less often than TorBox and a failed RD lookup just adds latency.
# RD stays as a fallback for the occasional title TorBox lacks.
_providers = [torbox, real_debrid]


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
