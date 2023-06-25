import os
import re
import requests
from dateutil.parser import parse

import asyncio
import aiohttp

import log
import settings
import torrent
from common import memoize


API_PATH = f"{settings.JACKETT_HOST}/api/v2.0"
API_KEY = settings.JACKETT_API_KEY


@memoize(3600)
def get_indexers():
    cache_dir = "/tmp/cache/jackett"

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    session = requests.Session()

    indexers_resp = session.get(
        f"{API_PATH}/indexers/all/results?apikey={API_KEY}"
    )
    indexers_json = indexers_resp.json()["Indexers"]
    return [i.get("ID") for i in indexers_json]


async def fetch_json(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except:
        return dict()


async def fetch_all(urls):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
        tasks = []
        for url in urls:
            tasks.append(asyncio.ensure_future(fetch_json(session, url)))

        json_responses = await asyncio.gather(*tasks)
        return json_responses


@memoize(300)
def search(searchterm):
    magnet_links = []
    try:
        results = []
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

        pattern = re.compile("\s(s\d\d)(e\d\d)?")
        season = None
        episode = None
        try:
            season = pattern.search(searchterm.lower())[1]
            episode = pattern.search(searchterm.lower())[2]
        except Exception as e:
            pass

        if season and (episode is None):

            def sort_by_only_season(x):
                pattern = re.compile("([e|E]\d\d)")
                try:
                    pattern.search(x.get("Title", ""))[0]
                    return 0
                except:
                    return 1

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
                    dict(
                        seeds=result.get("Seeders", 0),
                        title=result["Title"],
                        magnet=result.get("MagnetUri"),
                        torrent_link=result.get("Link"),
                        published=parse(published) if published else None,
                    )
                )
    except Exception:
        log.write_log()
    return magnet_links
