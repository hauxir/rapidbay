import os
import requests
from urllib.parse import unquote

import log


DEVICE_CODE = os.environ.get("RD_DEVICE_CODE")
CLIENT_ID = os.environ.get("RD_CLIENT_ID")
CLIENT_SECRET = os.environ.get("RD_CLIENT_SECRET")


def get_cached_url(magnet_hash, filename):
    """
    Get a RealDebrid download link for the given magnet hash.

    :param str
    magnet_hash: The hash of the magnet to get a download link for.
    :param str
    filename: The filename of the file to be downloaded from this torrent. If
    not provided, it will be assumed that there is only one file in this
    torrent and that it should be downloaded by default (i.e., without user
    interaction).
    """

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
            """
            Get a RealDebrid API response.

            :param path: The API endpoint to query.
            :type path: str

                :returns data: The JSON-decoded API response.
            :rtype data: dict
            """
            return requests.get(
                f"https://api.real-debrid.com/rest/1.0{path}",
                headers=dict(authorization=f"Bearer {access_token}"),
            ).json()

        def post(path, data):
            """
            This function makes a POST request to the Real-Debrid API.

            :param path:
            The URL path of the API endpoint.
            :type path: str

            :param data: The data to
            be sent in JSON format as part of the request body. 
                         Must be
            serializable into JSON using json.dumps(). 
                         Defaults to None,
            which sends an empty request body with this GET request (as opposed to
            sending no payload at all).

            :returns response_json: A dictionary
            containing information about whether or not this was a successful HTTP POST
            operation and what its contents are, if any (in JSON format).
            If successful, it will contain a 'status' key whose value is either "ok" or
            "bad_request". In case of success, it may also contain additional keys such
            as 'id', depending on what was passed in via data and where that particular
            endpoint redirects you too upon success (e.g., for torrent downloads)..
            If unsuccessful ('status' == "bad_request"), it will contain an 'error' key
            whose value is human readable text explaining why this failed; otherwise
            there would have been an internal server error 500 instead
            """
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
