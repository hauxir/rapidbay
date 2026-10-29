import asyncio
import os
import re
from typing import Any, AsyncIterator, Dict, List

import aiohttp
import log
import requests
import settings
import torrent
from common import memoize, should_drop_from_trending
from dateutil.parser import parse

API_PATH = f"{settings.JACKETT_HOST}/api/v2.0"
API_KEY = settings.JACKETT_API_KEY


@memoize(3600)
def get_indexers() -> List[str]:
    cache_dir = os.path.join(settings.CACHE_DIR, "jackett")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    session = requests.Session()

    indexers_resp = session.get(
        f"{API_PATH}/indexers/all/results?apikey={API_KEY}"
    )
    indexers_json = indexers_resp.json()["Indexers"]
    return [i.get("ID") for i in indexers_json]


async def fetch_json(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    try:
        async with session.get(url) as response:
            return await response.json()
    except (TimeoutError, aiohttp.ClientError):
        return {}  # Network or timeout error - return empty results


async def fetch_all(urls: List[str]) -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        tasks = []
        for url in urls:
            tasks.append(asyncio.ensure_future(fetch_json(session, url)))

        json_responses: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        return json_responses


def _build_urls(searchterm: str) -> List[str]:
    return [
        f"{API_PATH}/indexers/{indexer}/results?apikey={API_KEY}&Query={searchterm}"
        for indexer in get_indexers()
    ]


def _sort_results(results: List[Dict[str, Any]], searchterm: str) -> List[Dict[str, Any]]:
    results = sorted(results, key=lambda x: x.get("Seeders", 0), reverse=True)

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
            return 0 if episode_pattern.search(x.get("Title", "")) else 1

        results = sorted(results, key=sort_by_only_season, reverse=True)

    return results


def _parse_results(
    results: List[Dict[str, Any]], searchterm: str
) -> List[Dict[str, int | str | Any | None]]:
    magnet_links: List[Dict[str, int | str | Any | None]] = []
    hashes: List[str] = []

    for result in results:
        if searchterm == "":
            if result.get("TrackerId") in settings.EXCLUDE_TRACKERS_FROM_TRENDING:
                continue
            raw_cats: list[Any] = result.get("Category") or []
            cats = [c for c in raw_cats if isinstance(c, int)]
            if should_drop_from_trending(result.get("Title"), cats):
                continue
        if (result.get("Link") or result.get("MagnetUri")) and result.get(
            "Title"
        ):
            magnet_uri = result.get("MagnetUri")
            if magnet_uri:
                magnet_hash = torrent.get_hash(magnet_uri)
                if torrent.get_hash(magnet_uri) in hashes:
                    continue
                hashes.append(magnet_hash)
            if result.get("Seeders") == 0:
                continue
            published = result.get("PublishDate")
            magnet_links.append(
                {
                    "seeds": result.get("Seeders", 0),
                    "title": result["Title"],
                    "magnet": result.get("MagnetUri"),
                    "torrent_link": result.get("Link"),
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
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            tasks = [asyncio.ensure_future(fetch_json(session, url)) for url in urls]
            for task in asyncio.as_completed(tasks):
                data = await task
                parsed = _parse_results(
                    _sort_results(data.get("Results", []), searchterm), searchterm
                )
                if parsed:
                    yield parsed
    except (requests.RequestException, aiohttp.ClientError, KeyError, ValueError) as e:
        log.write_log()
        log.debug(f"Search failed: {e}")


@memoize(300)
def search(searchterm: str) -> List[Dict[str, int | str | Any | None]]:
    magnet_links: List[Dict[str, int | str | Any | None]] = []
    try:
        results: List[Dict[str, Any]] = []
        urls = _build_urls(searchterm)

        # asyncio.run() creates a fresh loop and, crucially, closes it (freeing
        # its epoll/eventfd file descriptors) in its finally. The old
        # new_event_loop()+set_event_loop() pattern never closed the loop, so
        # every search leaked ~2 fds — over time the daemon hit EMFILE
        # ("Too many open files") and crashed.
        responses = asyncio.run(fetch_all(urls))

        for data in responses:
            results = results + data.get("Results", [])

        magnet_links = _parse_results(_sort_results(results, searchterm), searchterm)
    except (requests.RequestException, aiohttp.ClientError, KeyError, ValueError) as e:
        log.write_log()
        log.debug(f"Search failed: {e}")
    return magnet_links
