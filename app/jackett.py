import aiohttp
import log
import settings


async def search(searchterm):
    magnet_links = []
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{settings.JACKETT_HOST}/api/v2.0/indexers/all/results?apikey={settings.JACKETT_API_KEY}&Query={searchterm}"
            ) as resp:
                data = await resp.json()
            results = data["Results"]
            for result in results:
                if result.get("MagnetUri") and result.get("Title"):
                    magnet_links.append(
                        dict(
                            seeds=result.get("Seeders", 0),
                            title=result["Title"],
                            magnet=result["MagnetUri"],
                        )
                    )
    except Exception:
        log.write_log()
    return magnet_links
