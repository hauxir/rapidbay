import os
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import log
import requests

RD_TOKEN = os.environ.get("RD_TOKEN")

def get_cached_url(magnet_hash: str, filename: str) -> Optional[str]:

    if not RD_TOKEN:
        return None

    try:
        def get(path: str) -> Dict[str, Any]:
            response = requests.get(
                f"https://api.real-debrid.com/rest/1.0{path}",
                headers={"authorization": f"Bearer {RD_TOKEN}"},
            )
            if not (200 <= response.status_code < 300):
                log.debug(f"Real Debrid GET failed: {path} - Status: {response.status_code}")
                return {}
            return response.json()

        def post(path: str, data: Dict[str, str]) -> Optional[Dict[str, Any]]:
            try:
                response = requests.post(
                    f"https://api.real-debrid.com/rest/1.0{path}",
                    data,
                    headers={"authorization": f"Bearer {RD_TOKEN}"},
                )
                if not (200 <= response.status_code < 300):
                    log.debug(f"Real Debrid POST failed: {path} - Status: {response.status_code}")
                    return None
                return response.json()
            except Exception as e:
                log.debug(f"Real Debrid POST exception: {path} - {str(e)}")
                return None

        result = post(
            "/torrents/addMagnet/",
            {"magnet": f"magnet:?xt=urn:btih:{magnet_hash}"},
        )
        if not result or "id" not in result:
            log.debug(f"Real Debrid: Failed to add magnet {magnet_hash}")
            return None
        torrent_id = result["id"]  # type: ignore

        select_result = post(f"/torrents/selectFiles/{torrent_id}", {"files": "all"})
        if not select_result:
            log.debug(f"Real Debrid: Failed to select files for torrent {torrent_id}")

        torrent_info = get(f"/torrents/info/{torrent_id}")
        if not torrent_info or "links" not in torrent_info:
            log.debug(f"Real Debrid: No links found for torrent {torrent_id}")
            return None

        links = torrent_info["links"][:30]
        unrestricted_links: List[Any] = []
        for link in links:
            unrestricted = post("/unrestrict/link", {"link": link})
            if unrestricted and "download" in unrestricted:
                unrestricted_links.append(unrestricted["download"])
            else:
                log.debug(f"Real Debrid: Failed to unrestrict link {link}")

        for _i, link in enumerate(unrestricted_links):
            if unquote(str(link)).endswith(filename):
                return str(link)

        log.debug(f"Real Debrid: File {filename} not found in torrent {magnet_hash}")

    except Exception as e:
        log.debug(f"Real Debrid: Unexpected error for {magnet_hash}: {str(e)}")
        log.write_log()

    return None
