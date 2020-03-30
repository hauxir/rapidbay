import aiohttp
import log
import settings
from bs4 import BeautifulSoup


async def search(searchterm):
    magnet_links = []
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"https://{settings.PIRATEBAY_HOST}/s/?q={searchterm}&category=0&page=0&orderby=99"
            ) as resp:
                data = await resp.text()
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
