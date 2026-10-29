import asyncio
import re
from typing import Any, AsyncIterator, Dict, List, cast
from urllib.parse import urlencode

import aiohttp
import log
import requests
import settings
import torrent
from common import memoize, should_drop_from_trending
from dateutil.parser import parse

API_PATH = f"{settings.PROWLARR_HOST}/api/v1"
API_KEY = settings.PROWLARR_API_KEY


def _extract_magnet(result: Dict[str, Any]) -> str | None:
    """Return a real magnet: URI from a Prowlarr result, if one is directly available.

    Prowlarr's `magnetUrl` is often its own proxy URL that 302-redirects to the
    actual magnet, so it's not a magnet by itself. The real magnet is usually
    in `guid` for indexers like ThePirateBay; for others, we fall back to
    constructing one from `infoHash` if present.
    """
    for key in ("magnetUrl", "guid"):
        v = result.get(key)
        if isinstance(v, str) and v.startswith("magnet:?xt=urn:btih:"):
            return v
    info_hash = result.get("infoHash")
    title = result.get("title")
    if isinstance(info_hash, str) and info_hash and isinstance(title, str):
        from urllib.parse import quote
        return f"magnet:?xt=urn:btih:{info_hash.lower()}&dn={quote(title)}"
    return None


def _extract_torrent_link(result: Dict[str, Any]) -> str | None:
    """Return a URL the daemon can download/redirect-resolve to obtain the torrent."""
    for key in ("downloadUrl", "magnetUrl"):
        v = result.get(key)
        if isinstance(v, str) and v and not v.startswith("magnet:"):
            return v
    guid = result.get("guid")
    if isinstance(guid, str) and guid.startswith(("http://", "https://")):
        return guid
    return None


@memoize(3600)
def get_indexer_ids() -> List[int]:
    resp = requests.get(
        f"{API_PATH}/indexer",
        headers={"X-Api-Key": API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return [i["id"] for i in data if isinstance(i, dict) and i.get("enable")]


async def fetch_json(session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
    try:
        async with session.get(url) as response:
            data: Any = await response.json()
            if not isinstance(data, list):
                return []
            return [r for r in data if isinstance(r, dict)]  # type: ignore[reportUnknownVariableType]
    except (TimeoutError, aiohttp.ClientError):
        return []


async def fetch_all(urls: List[str]) -> List[List[Dict[str, Any]]]:
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=5),
        headers={"X-Api-Key": API_KEY},
    ) as session:
        tasks = [asyncio.ensure_future(fetch_json(session, url)) for url in urls]
        return await asyncio.gather(*tasks)


def _build_urls(searchterm: str) -> List[str]:
    return [
        f"{API_PATH}/search?{urlencode({'query': searchterm, 'type': 'search', 'limit': 100, 'indexerIds': iid})}"
        for iid in get_indexer_ids()
    ]


def _sort_results(results: List[Dict[str, Any]], searchterm: str) -> List[Dict[str, Any]]:
    # Prowlarr can also return usenet results; only torrents are usable here
    results = [
        r for r in results if r.get("protocol", "torrent") == "torrent"
    ]

    results = sorted(results, key=lambda x: x.get("seeders", 0) or 0, reverse=True)

    pattern = re.compile(r"\s(s\d\d)(e\d\d)?")
    season = None
    episode = None
    match = pattern.search(searchterm.lower())
    if match:
        season = match.group(1)
        episode = match.group(2)

    if season and (episode is None):

        def sort_by_only_season(x: Dict[str, Any]) -> int:
            episode_pattern = re.compile(r"[eE]\d\d")
            return 0 if episode_pattern.search(x.get("title", "")) else 1

        results = sorted(results, key=sort_by_only_season, reverse=True)

    return results


def _parse_results(
    results: List[Dict[str, Any]], searchterm: str
) -> List[Dict[str, int | str | Any | None]]:
    magnet_links: List[Dict[str, int | str | Any | None]] = []
    hashes: List[str] = []

    for result in results:
        indexer = result.get("indexer") or ""
        title = result.get("title")
        if searchterm == "":
            if indexer in settings.EXCLUDE_TRACKERS_FROM_TRENDING:
                continue
            raw_categories: list[Any] = result.get("categories") or []
            cats: list[int] = []
            for c in raw_categories:
                if isinstance(c, dict):
                    cid = cast("dict[str, Any]", c).get("id")
                    if isinstance(cid, int):
                        cats.append(cid)
            if should_drop_from_trending(title, cats):
                continue
        if not title:
            continue

        magnet_uri = _extract_magnet(result)
        torrent_link = _extract_torrent_link(result)
        if not (magnet_uri or torrent_link):
            continue

        if magnet_uri:
            magnet_hash = torrent.get_hash(magnet_uri)
            if magnet_hash in hashes:
                continue
            hashes.append(magnet_hash)

        if (result.get("seeders") or 0) == 0:
            continue

        published = result.get("publishDate")
        magnet_links.append(
            {
                "seeds": result.get("seeders", 0) or 0,
                "title": title,
                "magnet": magnet_uri,
                "torrent_link": torrent_link,
                "published": parse(published) if published else None,
            }
        )
    return magnet_links


async def search_stream(
    searchterm: str,
) -> AsyncIterator[List[Dict[str, int | str | Any | None]]]:
    """Yield parsed result batches as each indexer responds, fastest first."""
    try:
        urls = await asyncio.to_thread(_build_urls, searchterm)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5),
            headers={"X-Api-Key": API_KEY},
        ) as session:
            tasks = [asyncio.ensure_future(fetch_json(session, url)) for url in urls]
            for task in asyncio.as_completed(tasks):
                data = await task
                parsed = _parse_results(_sort_results(data, searchterm), searchterm)
                if parsed:
                    yield parsed
    except (requests.RequestException, aiohttp.ClientError, KeyError, ValueError) as e:
        log.write_log()
        log.debug(f"Prowlarr search failed: {e}")


@memoize(300)
def search(searchterm: str) -> List[Dict[str, int | str | Any | None]]:
    magnet_links: List[Dict[str, int | str | Any | None]] = []
    try:
        urls = _build_urls(searchterm)

        # asyncio.run() creates a fresh loop and, crucially, closes it (freeing
        # its epoll/eventfd file descriptors) in its finally. The old
        # new_event_loop()+set_event_loop() pattern never closed the loop, so
        # every search leaked ~2 fds — over time the daemon hit EMFILE
        # ("Too many open files") and crashed.
        responses = asyncio.run(fetch_all(urls))

        results: List[Dict[str, Any]] = []
        for data in responses:
            results.extend(data)

        magnet_links = _parse_results(_sort_results(results, searchterm), searchterm)
    except (requests.RequestException, aiohttp.ClientError, KeyError, ValueError) as e:
        log.write_log()
        log.debug(f"Prowlarr search failed: {e}")
    return magnet_links
