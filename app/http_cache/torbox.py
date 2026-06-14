import json
import os
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote

import common
import log
import requests
import settings

TB_TOKEN = os.environ.get("TB_TOKEN")

API_BASE = "https://api.torbox.app/v1/api"


def _get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    response = requests.get(
        f"{API_BASE}{path}",
        params=params,
        headers={"authorization": f"Bearer {TB_TOKEN}"},
    )
    if not (200 <= response.status_code < 300):
        log.debug(f"TorBox GET failed: {path} - Status: {response.status_code}")
        return {}
    return response.json()


def _post(path: str, data: Dict[str, str]) -> Dict[str, Any] | None:
    try:
        response = requests.post(
            f"{API_BASE}{path}",
            data,
            headers={"authorization": f"Bearer {TB_TOKEN}"},
        )
        if not (200 <= response.status_code < 300):
            log.debug(f"TorBox POST failed: {path} - Status: {response.status_code}")
            return None

        # Some endpoints return empty responses on success
        if not response.text.strip():
            return {}

        return response.json()
    except Exception as e:
        log.debug(f"TorBox POST exception: {path} - {str(e)}")
        return None


def _add_magnet(magnet_hash: str) -> Any:
    """Add a magnet to TorBox and return the torrent id."""
    result = _post(
        "/torrents/createtorrent",
        {"magnet": f"magnet:?xt=urn:btih:{magnet_hash}"},
    )
    if not result or not result.get("success") or "data" not in result:
        log.debug(f"TorBox: Failed to add magnet {magnet_hash}")
        return None

    data = result["data"]
    if "torrent_id" in data:
        return data["torrent_id"]
    return data.get("id")


def _get_torrent_info(torrent_id: Any) -> Dict[str, Any]:
    result = _get("/torrents/mylist", {"id": torrent_id, "bypass_cache": "true"})
    if not result or not result.get("success") or "data" not in result:
        return {}
    return result["data"]


def get_cached_url(magnet_hash: str, filename: str) -> str | None:

    if not TB_TOKEN:
        return None

    try:
        torrent_id = _add_magnet(magnet_hash)
        if torrent_id is None:
            return None

        torrent_info = _get_torrent_info(torrent_id)
        if not torrent_info or "files" not in torrent_info:
            log.debug(f"TorBox: No info found for torrent {torrent_id}")
            return None

        files = torrent_info["files"]
        file_entries: List[Tuple[str, Any]] = [
            (str(f.get("name") or f.get("path")), f.get("id"))
            for f in files
            if isinstance(f, dict) and f.get("id") is not None and (f.get("name") or f.get("path"))
        ]

        normalized_filename = common.normalize_filename(filename)
        for path, file_id in file_entries:
            if common.normalize_filename(unquote(path)).endswith(normalized_filename):
                dl = _get(
                    "/torrents/requestdl",
                    {
                        "token": TB_TOKEN,
                        "torrent_id": torrent_id,
                        "file_id": file_id,
                    },
                )
                if dl and dl.get("success") and dl.get("data"):
                    return str(dl["data"])
                log.debug(f"TorBox: Failed to request download link for {filename}")

        log.debug(f"TorBox: File {filename} not found in torrent {magnet_hash}")

    except Exception as e:
        log.debug(f"TorBox: Unexpected error for {magnet_hash}: {str(e)}")
        log.write_log()

    return None


def get_filelist(magnet_hash: str) -> List[str] | None:
    """Get filelist from TorBox for a given magnet hash"""
    if not TB_TOKEN:
        return None

    try:
        torrent_id = _add_magnet(magnet_hash)
        if torrent_id is None:
            return None

        torrent_info = _get_torrent_info(torrent_id)
        if not torrent_info or "files" not in torrent_info:
            return None

        files = torrent_info["files"]
        file_paths: List[str] = [
            str(f.get("name") or f.get("path")).lstrip("/")
            for f in files
            if isinstance(f, dict) and (f.get("name") or f.get("path"))
        ]

        # Write to cache file only if we got results
        if file_paths:
            cache_filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
            os.makedirs(settings.FILELIST_DIR, exist_ok=True)
            with open(cache_filename, 'w') as f:
                json.dump(file_paths, f)

        return file_paths

    except Exception as e:
        log.debug(f"TorBox filelist error for {magnet_hash}: {str(e)}")
        return None
