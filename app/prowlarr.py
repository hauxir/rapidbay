import re
from typing import Any, Dict, List

import log
import requests
import settings
import torrent
from common import memoize
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


@memoize(300)
def search(searchterm: str) -> List[Dict[str, int | str | Any | None]]:
    magnet_links: List[Dict[str, int | str | Any | None]] = []
    try:
        params = {
            "query": searchterm,
            "type": "search",
            "limit": 100,
            "apikey": API_KEY,
        }
        headers = {"X-Api-Key": API_KEY}
        resp = requests.get(
            f"{API_PATH}/search", params=params, headers=headers, timeout=15
        )
        results: List[Dict[str, Any]] = resp.json() or []

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

        hashes: List[str] = []

        for result in results:
            indexer = result.get("indexer") or ""
            if (
                searchterm == ""
                and indexer in settings.EXCLUDE_TRACKERS_FROM_TRENDING
            ):
                continue
            title = result.get("title")
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
    except (requests.RequestException, KeyError, ValueError) as e:
        log.write_log()
        log.debug(f"Prowlarr search failed: {e}")
    return magnet_links
