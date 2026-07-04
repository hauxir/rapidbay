import contextlib
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import settings

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

def _write_filelist_to_disk(magnet_hash: str, filelist: List[str]) -> None:
    """Cache the filelist so the next request short-circuits before any network
    call. Written via a temp file + atomic replace so concurrent requests for the
    same hash can't observe a half-written file."""
    os.makedirs(settings.FILELIST_DIR, exist_ok=True)
    cache_filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    # A unique temp file (in the same dir, so os.replace stays atomic) — a
    # PID-only name would collide when two threads cache the same hash at once,
    # letting their interleaved writes publish a half-written file.
    fd, tmp_filename = tempfile.mkstemp(dir=settings.FILELIST_DIR, prefix=f"{magnet_hash}.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(filelist, f)
        os.replace(tmp_filename, cache_filename)
    except BaseException:
        # Best-effort cleanup so a failed write doesn't leak the temp file.
        with contextlib.suppress(OSError):
            os.remove(tmp_filename)
        raise


def get_cached_filelist(magnet_hash: str) -> List[str] | None:
    """Query every provider concurrently and return the first non-empty filelist,
    so adding a second provider doesn't add it to the critical-path latency. The
    losing provider's request is left to finish in the background (it has no side
    effects once we've returned)."""
    executor = ThreadPoolExecutor(max_workers=len(_providers))
    try:
        futures = [
            executor.submit(provider.get_filelist, magnet_hash)
            for provider in _providers
        ]
        for future in as_completed(futures):
            filelist = future.result()
            if filelist:
                _write_filelist_to_disk(magnet_hash, filelist)
                return filelist
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
