import re
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

        results = sorted(results, key=lambda x: x.get("Seeders", 0), reverse=True)

        pattern = re.compile("\s(s\d\d)(e\d\d)?")
        season = None
        episode = None
        try:
            season = pattern.search(searchterm.lower())[1]
            episode = pattern.search(searchterm.lower())[2]
        except Exception as e:
            pass

        if season and (episode is None):

            def sort_by_only_season(x):
                pattern = re.compile("([e|E]\d\d)")
                try:
                    pattern.search(x.get("Title", ""))[0]
                    return 0
                except:
                    return 1

            results = sorted(results, key=sort_by_only_season, reverse=True)

        for result in results:
            if (
                searchterm == ""
                and result.get("TrackerId") in settings.EXCLUDE_TRACKERS_FROM_TRENDING
            ):
                continue
            elif (result.get("Link") or result.get("MagnetUri")) and result.get(
                "Title"
            ):
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
                        published=parse(published) if published else None,
                    )
                )
    except Exception:
        log.write_log()
    return magnet_links
