import os
import requests
from urllib.parse import unquote

import log


DEVICE_CODE = os.environ.get("RD_DEVICE_CODE")
CLIENT_ID = os.environ.get("RD_CLIENT_ID")
CLIENT_SECRET = os.environ.get("RD_CLIENT_SECRET")


def get_cached_url(magnet_hash, filename):

    if not any([DEVICE_CODE, CLIENT_ID, CLIENT_SECRET]):
        return None

    try:

        creds = requests.post(
            "https://api.real-debrid.com/oauth/v2/token",
            dict(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                code=DEVICE_CODE,
                grant_type="http://oauth.net/grant_type/device/1.0",
            ),
        ).json()

        access_token = creds["access_token"]

        def get(path):
            return requests.get(
                f"https://api.real-debrid.com/rest/1.0{path}",
                headers=dict(authorization=f"Bearer {access_token}"),
            ).json()

        def post(path, data):
            try:
                return requests.post(
                    f"https://api.real-debrid.com/rest/1.0{path}",
                    data,
                    headers=dict(authorization=f"Bearer {access_token}"),
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
