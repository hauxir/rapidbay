import os
import requests
import cachetools.func
from urllib.parse import unquote

import log


DEVICE_CODE = os.environ.get("RD_DEVICE_CODE")
CLIENT_ID = os.environ.get("RD_CLIENT_ID")
CLIENT_SECRET = os.environ.get("RD_CLIENT_SECRET")


@cachetools.func.ttl_cache(ttl=60*60)
def _get_token():
    creds = requests.post(
        "https://api.real-debrid.com/oauth/v2/token",
        dict(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            code=DEVICE_CODE,
            grant_type="http://oauth.net/grant_type/device/1.0",
        ),
    ).json()
    return creds["access_token"]


@cachetools.func.ttl_cache(ttl=60*60)
def _get(path):
    access_token = _get_token()
    return requests.get(
        f"https://api.real-debrid.com/rest/1.0{path}",
        headers=dict(authorization=f"Bearer {access_token}"),
    ).json()


def _post(path, data):
    access_token = _get_token()
    try:
        return requests.post(
            f"https://api.real-debrid.com/rest/1.0{path}",
            data,
            headers=dict(authorization=f"Bearer {access_token}"),
        ).json()
    except:
        return None


def get_cached_filelist(magnet_hash):

    if not any([DEVICE_CODE, CLIENT_ID, CLIENT_SECRET]):
        return None

    try:
        result = _post(
            "/torrents/addMagnet/",
            dict(magnet=f"magnet:?xt=urn:btih:{magnet_hash}"),
        )
        torrent_id = result.get("id")
        if torrent_id:
            info = _get(f"/torrents/info/{torrent_id}")
            original_name = info.get("original_filename","")
            is_single_file = len(info.get("files",[])) == 1 and original_name == info["files"][0].get("path")[1:]
            if is_single_file:
                filelist = [info["files"][0].get("path")[1:]]
            else:
                filelist = [os.path.join(original_name, f.get("path","")[1:]) for f in info.get("files", [])]
            return filelist

    except Exception as e:
        log.write_log()

    return None


def get_cached_url(magnet_hash, filename):

    if not any([DEVICE_CODE, CLIENT_ID, CLIENT_SECRET]):
        return None

    try:

        instant = _get(f"/torrents/instantAvailability/{magnet_hash}")
        result = instant.get(magnet_hash)
        rd = result.get("rd") if isinstance(result, dict) else None
        if rd:
            result = _post(
                "/torrents/addMagnet/",
                dict(magnet=f"magnet:?xt=urn:btih:{magnet_hash}"),
            )
            torrent_id = result["id"]
            _post(f"/torrents/selectFiles/{torrent_id}", dict(files="all"))
            info = _get(f"/torrents/info/{torrent_id}")
            links = info["links"][:30]
            unrestricted_links = [
                _post("/unrestrict/link", dict(link=link))["download"] for link in links
            ]
            for i, link in enumerate(unrestricted_links):
                if unquote(link).endswith(filename):
                    return link

    except Exception as e:
        log.write_log()

    return None
