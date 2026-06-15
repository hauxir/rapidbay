from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

from . import real_debrid, torbox

# Both providers are offered to libtorrent as separate web seeds when they each
# have the file cached, so the download fans out across them in parallel and
# libtorrent recombines the pieces (it stays the sole writer and hash-verifies
# every piece). TorBox is listed first only so it wins ties in display order —
# Real Debrid DMCA-blocks (HTTP 451) most popular content and answers far less
# often.
_providers = [torbox, real_debrid]
_by_name = {p.__name__.rsplit(".", 1)[-1]: p for p in _providers}


def get_cached_urls(magnet_hash: str, filename: str) -> List[Tuple[str, str]]:
    """Resolve the debrid URL from every provider that has the file cached,
    returning (provider_name, url) pairs. Providers are queried concurrently so
    adding a second provider doesn't add it to the critical-path latency."""
    with ThreadPoolExecutor(max_workers=len(_by_name)) as executor:
        futures = {
            name: executor.submit(provider.get_cached_url, magnet_hash, filename)
            for name, provider in _by_name.items()
        }
    return [
        (name, url)
        for name, future in futures.items()
        if (url := future.result())
    ]


def get_provider_url(provider_name: str, magnet_hash: str, filename: str) -> str | None:
    """Re-resolve the URL from a single provider (used to refresh a stale link)."""
    provider = _by_name.get(provider_name)
    if provider is None:
        return None
    return provider.get_cached_url(magnet_hash, filename)


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
