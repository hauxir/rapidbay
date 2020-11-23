import requests
import log
import settings


def search(searchterm):
    magnet_links = []
    try:
        resp = requests.get(
            f"{settings.JACKETT_HOST}/api/v2.0/indexers/all/results?apikey={settings.JACKETT_API_KEY}&Query={searchterm}"
        )
        data = resp.json()
        results = data["Results"]
        for result in results:
            if (result.get("Link") or result.get("MagnetUri")) and result.get("Title"):
                magnet_links.append(
                    dict(
                        seeds=result.get("Seeders", 0),
                        title=result["Title"],
                        magnet=result.get("MagnetUri"),
                        torrent_link=result.get("Link")
                    )
                )
    except Exception:
        log.write_log()
    return magnet_links
