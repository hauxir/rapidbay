import requests
from dateutil.parser import parse

import log
import settings
import torrent


def search(searchterm):
    magnet_links = []
    try:
        resp = requests.get(
            f"{settings.JACKETT_HOST}/api/v2.0/indexers/all/results?apikey={settings.JACKETT_API_KEY}&Query={searchterm}"
        )
        data = resp.json()
        results = data["Results"]
        hashes = []
        for result in results:
            if (result.get("Link") or result.get("MagnetUri")) and result.get("Title"):
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
                        published=parse(published) if published else None
                    )
                )
    except Exception:
        log.write_log()
    return magnet_links
