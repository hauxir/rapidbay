import requests
import log
import settings

from bs4 import BeautifulSoup


def search(searchterm):
    magnet_links = []
    try:
        resp = requests.get(
            f"https://{settings.PIRATEBAY_HOST}/s/?q={searchterm}&category=0&page=0&orderby=99"
        )
        data = resp.text
        soup = BeautifulSoup(data, "html.parser")
        trs = soup.find(id="searchResult").find_all("tr")
        for tr in trs:
            try:
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                td = tds[1]
                try:
                    seeds = int(tr.find_all("td")[2].contents[0])
                except ValueError:
                    seeds = 0
                a = td.find_all("a")
                title = str(a[0].contents[0])
                magnet_link = str(a[1]["href"])
                if seeds:
                    magnet_links.append(
                        dict(title=title, magnet=magnet_link, seeds=seeds)
                    )
            except Exception:
                log.write_log()
    except Exception:
        log.write_log()
    return magnet_links
