import os
import requests
from urllib.parse import unquote

import log

RD_TOKEN = os.environ.get("RD_TOKEN")

def get_cached_url(magnet_hash, filename):

    if not RD_TOKEN:
        return None

    try:
        def get(path):
            return requests.get(
                f"https://api.real-debrid.com/rest/1.0{path}",
                headers=dict(authorization=f"Bearer {RD_TOKEN}"),
            ).json()

        def post(path, data):
            try:
                return requests.post(
                    f"https://api.real-debrid.com/rest/1.0{path}",
                    data,
                    headers=dict(authorization=f"Bearer {RD_TOKEN}"),
                ).json()
            except:
                return None

        instant = get(f"/torrents/instantAvailability/{magnet_hash}")
        result = instant.get(magnet_hash)
        rd = result.get("rd") if isinstance(result, dict) else None
        if rd:
            result = post(
                "/torrents/addMagnet/",
                dict(magnet=f"magnet:?xt=urn:btih:{magnet_hash}"),
            )
            torrent_id = result["id"]
            post(f"/torrents/selectFiles/{torrent_id}", dict(files="all"))
            links = get(f"/torrents/info/{torrent_id}")["links"][:30]
            unrestricted_links = [
                post("/unrestrict/link", dict(link=link))["download"] for link in links
            ]
            for i, link in enumerate(unrestricted_links):
                if unquote(link).endswith(filename):
                    return link

    except Exception as e:
        log.write_log()

    return None
