import os
import requests
from typing import Any, Dict, Optional
from urllib.parse import unquote

import log

RD_TOKEN = os.environ.get("RD_TOKEN")

def get_cached_url(magnet_hash: str, filename: str) -> Optional[str]:

    if not RD_TOKEN:
        return None

    try:
        def get(path: str) -> Dict[str, Any]:
            return requests.get(
                f"https://api.real-debrid.com/rest/1.0{path}",
                headers=dict(authorization=f"Bearer {RD_TOKEN}"),
            ).json()

        def post(path: str, data: Dict[str, str]) -> Optional[Dict[str, Any]]:
            try:
                return requests.post(
                    f"https://api.real-debrid.com/rest/1.0{path}",
                    data,
                    headers=dict(authorization=f"Bearer {RD_TOKEN}"),
                ).json()
            except:
                return None

        result = post(
            "/torrents/addMagnet/",
            dict(magnet=f"magnet:?xt=urn:btih:{magnet_hash}"),
        )
        torrent_id = result["id"]  # type: ignore
        post(f"/torrents/selectFiles/{torrent_id}", dict(files="all"))
        links = get(f"/torrents/info/{torrent_id}")["links"][:30]
        unrestricted_links = [
            post("/unrestrict/link", dict(link=link))["download"] for link in links  # type: ignore
        ]
        for i, link in enumerate(unrestricted_links):
            if unquote(link).endswith(filename):
                return link

    except Exception as e:
        log.write_log()

    return None
