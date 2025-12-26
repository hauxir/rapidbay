import asyncio
import os
import re
from typing import Any, Dict, List, Optional, Union

import aiohttp
import log
import requests
import settings
import torrent
from common import memoize
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
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return {}  # Network or timeout error - return empty results


async def fetch_all(urls: List[str]) -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        tasks = []
        for url in urls:
            tasks.append(asyncio.ensure_future(fetch_json(session, url)))

        json_responses: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        return json_responses


@memoize(300)
def search(searchterm: str) -> List[Dict[str, Union[int, str, Optional[Any]]]]:
    magnet_links: List[Dict[str, Union[int, str, Optional[Any]]]] = []
    try:
        results: List[Dict[str, Any]] = []
        urls = [
            f"{API_PATH}/indexers/{indexer}/results?apikey={API_KEY}&Query={searchterm}"
            for indexer in get_indexers()
        ]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        responses = loop.run_until_complete(fetch_all(urls))

        for data in responses:
            results = results + data.get("Results", [])

        hashes = []

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

        for result in results:
            if (
                searchterm == ""
                and result.get("TrackerId") in settings.EXCLUDE_TRACKERS_FROM_TRENDING
            ):
                continue
            elif (result.get("Link") or result.get("MagnetUri")) and result.get(
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
    except (requests.RequestException, aiohttp.ClientError, KeyError, ValueError) as e:
        log.write_log()
        log.debug(f"Search failed: {e}")
    return magnet_links
