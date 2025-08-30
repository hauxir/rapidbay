import sys
import time
from urllib.parse import parse_qsl, quote, urlencode

import requests
import xbmcgui
import xbmcplugin


class RapidbayClient:
    def __init__(self, rootpath, password=None):
        self.rootpath = rootpath
        self.password = password

    def search(self, query):
        return self._get(f"/api/search/{quote(query)}")

    def torrent_url_to_magnet(self, url):
        return self._post("/api/torrent_url_to_magnet/", {"url": url})["magnet_link"]

    def files(self, magnet_link):
        magnet_hash = self._magnet_link_to_hash(magnet_link)
        files = None
        while files is None:
            result = self._get(f"/api/magnet/{magnet_hash}/")
            files = result.get("files")
        return files

    def magnet_download(self, magnet_link, filename):
        return self._post(
            "/api/magnet_download/", {"magnet_link": magnet_link, "filename": filename}
        )

    def file_status(self, magnet_hash, filename):
        return self._get(f"/api/magnet/{magnet_hash}/{quote(filename)}")

    def next_file(self, magnet_hash, filename):
        return self._get(f"/api/next_file/{magnet_hash}/{quote(filename)}")

    def _magnet_link_to_hash(self, magnet_link):
        return self._post("/api/magnet_files/", {"magnet_link": magnet_link})[
            "magnet_hash"
        ]

    def _request(self, method, path, data=None):
        url = f"{self.rootpath}{path}"
        cookies = {"password": self.password}
        if method == "get":
            return requests.get(url, cookies=cookies).json()
        if method == "post":
            return requests.post(url, cookies=cookies, data=data).json()

    def get_play_url(self, magnet_hash, filename):
        return f"{self.rootpath}/play/{magnet_hash}/{quote(filename)}"

    def _get(self, path):
        return self._request("get", path)

    def _post(self, path, data):
        return self._request("post", path, data)


client = RapidbayClient(__host__, __password__)


def get_url(**kwargs):
    return f"{__url__}?{urlencode(kwargs)}"


def root():
    xbmcplugin.addDirectoryItem(
        __handle__,
        get_url(action="listing", category="search"),
        xbmcgui.ListItem(label="Search"),
        True,
    )
    xbmcplugin.addDirectoryItem(
        __handle__,
        get_url(action="listing"),
        xbmcgui.ListItem(label="Trending"),
        True,
    )
    xbmcplugin.endOfDirectory(__handle__)


def search():
    dialog = xbmcgui.Dialog()
    query = dialog.input("Query")
    if query:
        show_search_results(query)


def show_search_results(query):
    for result in client.search(query).get("results", []):
        magnet = result.get("magnet") or ""
        urlargs = {"action": "listing", "torrent_link": result.get("torrent_link")}
        if magnet:
            urlargs["magnet"] = magnet
        xbmcplugin.addDirectoryItem(
            __handle__,
            get_url(**urlargs),
            xbmcgui.ListItem(label=result.get("title")),
            True,
        )
    xbmcplugin.endOfDirectory(__handle__)


def view_files(magnet_link):
    for file in client.files(magnet_link):
        li = xbmcgui.ListItem(label=file)
        li.setProperty("IsPlayable", "true")
        li.setInfo("video", {"Title": file})
        xbmcplugin.addDirectoryItem(
            __handle__,
            get_url(action="play", magnet_link=magnet_link, filename=file),
            li,
            False,
        )
    xbmcplugin.endOfDirectory(__handle__)


def play(magnet_link, filename):
    magnet_hash = client.magnet_download(magnet_link, filename)["magnet_hash"]
    completed = False
    progress = xbmcgui.DialogProgress()
    progress.create("Preparing file...", "")
    finished_filename = None
    while not completed:
        status = client.file_status(magnet_hash, filename)
        status_str = status.get("status")
        progress_percentage = int(status.get("progress", 0) * 100)
        peers = status.get("peers")
        if status_str != "ready":
            if progress_percentage > 0:
                status_str = status_str + f" ({progress_percentage}%)"
            if peers is not None:
                status_str = status_str + f", {peers} peers"
        status_str = status_str.replace("_", " ").title()
        progress.update(progress_percentage, status_str)
        finished_filename = status.get("filename")
        completed = status_str == "Ready"
        if progress.iscanceled() or completed:
            break
        time.sleep(1)
    next_file = client.next_file(magnet_hash, filename)["next_filename"]
    if next_file:
        client.magnet_download(magnet_link, next_file)
    play_url = client.get_play_url(magnet_hash, finished_filename)
    xbmcplugin.setResolvedUrl(__handle__, True, xbmcgui.ListItem(path=play_url))


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params["action"] == "listing":
            if params.get("category") == "search":
                search()
            elif params.get("magnet") or params.get("torrent_link"):
                magnet = params.get("magnet") or client.torrent_url_to_magnet(
                    params.get("torrent_link")
                )
                view_files(magnet)
            else:
                show_search_results("")
        elif params["action"] == "play":
            magnet_link = params.get("magnet_link")
            filename = params.get("filename")
            play(magnet_link, filename)
    else:
        root()


if __name__ == "__main__":
    router(sys.argv[2][1:])
