import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import log
import requests
import settings

RD_TOKEN = os.environ.get("RD_TOKEN")


def _get(path: str) -> Dict[str, Any]:
    response = requests.get(
        f"https://api.real-debrid.com/rest/1.0{path}",
        headers={"authorization": f"Bearer {RD_TOKEN}"},
    )
    if not (200 <= response.status_code < 300):
        log.debug(f"Real Debrid GET failed: {path} - Status: {response.status_code}")
        return {}
    return response.json()


def _post(path: str, data: Dict[str, str]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.post(
            f"https://api.real-debrid.com/rest/1.0{path}",
            data,
            headers={"authorization": f"Bearer {RD_TOKEN}"},
        )
        if not (200 <= response.status_code < 300):
            log.debug(f"Real Debrid POST failed: {path} - Status: {response.status_code}")
            return None

        # Some endpoints return empty responses on success (like selectFiles)
        if not response.text.strip():
            return {}

        return response.json()
    except Exception as e:
        log.debug(f"Real Debrid POST exception: {path} - {str(e)}")
        return None


def get_cached_url(magnet_hash: str, filename: str) -> Optional[str]:

    if not RD_TOKEN:
        return None

    try:

        result = _post(
            "/torrents/addMagnet/",
            {"magnet": f"magnet:?xt=urn:btih:{magnet_hash}"},
        )
        if not result or "id" not in result:
            log.debug(f"Real Debrid: Failed to add magnet {magnet_hash}")
            return None
        torrent_id = result["id"]

        select_result = _post(f"/torrents/selectFiles/{torrent_id}", {"files": "all"})
        if not select_result:
            log.debug(f"Real Debrid: Failed to select files for torrent {torrent_id}")

        torrent_info = _get(f"/torrents/info/{torrent_id}")
        if not torrent_info or "links" not in torrent_info:
            log.debug(f"Real Debrid: No links found for torrent {torrent_id}")
            return None

        links = torrent_info["links"][:30]
        unrestricted_links: List[Any] = []
        for link in links:
            unrestricted = _post("/unrestrict/link", {"link": link})
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


def get_filelist(magnet_hash: str) -> Optional[List[str]]:
    """Get filelist from Real-Debrid for a given magnet hash"""
    if not RD_TOKEN:
        return None

    try:
        result = _post(
            "/torrents/addMagnet/",
            {"magnet": f"magnet:?xt=urn:btih:{magnet_hash}"},
        )
        if not result or "id" not in result:
            return None
        torrent_id = result["id"]

        torrent_info = _get(f"/torrents/info/{torrent_id}")
        if not torrent_info or "files" not in torrent_info:
            return None

        files = torrent_info["files"]
        file_paths: List[str] = [f.get("path", "").lstrip("/") for f in files if isinstance(f, dict) and f.get("path")]

        # Write to cache file only if we got results
        if file_paths:
            cache_filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
            os.makedirs(settings.FILELIST_DIR, exist_ok=True)
            with open(cache_filename, 'w') as f:
                json.dump(file_paths, f)

        return file_paths

    except Exception as e:
        log.debug(f"Real Debrid filelist error for {magnet_hash}: {str(e)}")
        return None
