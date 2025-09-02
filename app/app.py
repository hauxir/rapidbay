import contextlib
import datetime
import json
import os
import random
import string
import subprocess
import urllib.parse
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import http_cache
import jackett
import PTN
import requests
import settings
import torrent
from common import path_hierarchy
from flask import Flask, Response, abort, jsonify, request, send_from_directory
from rapidbaydaemon import DaemonClient, FileStatus, get_filepaths
from requests.adapters import HTTPAdapter
from werkzeug.exceptions import NotFound
from werkzeug.middleware.proxy_fix import ProxyFix

app: Flask = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['USE_X_SENDFILE'] = True
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

daemon: DaemonClient = DaemonClient()

# Global session for connection pooling
_session = requests.Session()
_session.mount('http://', HTTPAdapter(pool_connections=5, pool_maxsize=5))
_session.mount('https://', HTTPAdapter(pool_connections=5, pool_maxsize=5))


@app.after_request
def add_header(response: Response) -> Response:
    set_cookie = response.headers.get("set-cookie")
    if set_cookie:
        response.headers["x-set-cookie"] = set_cookie
    return response


@app.after_request
def after_request(resp: Response) -> Response:
    x_sendfile: Optional[str] = resp.headers.get("X-Sendfile")
    if x_sendfile:
        resp.headers["X-Accel-Redirect"] = urllib.parse.quote(f"/nginx/{x_sendfile}")
        del resp.headers["X-Sendfile"]
    resp.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    return resp


def _get_files(magnet_hash: str) -> Optional[List[str]]:
    filepaths: Optional[List[str]] = get_filepaths(magnet_hash)

    if not filepaths:
        filepaths = http_cache.real_debrid.get_filelist(magnet_hash)

    if filepaths:
        files: List[str] = [os.path.basename(f) for f in filepaths]
        supported_files: List[str] = [
            f
            for f in files
            if any(f.endswith(f".{ext}") for ext in settings.SUPPORTED_EXTENSIONS)
        ]

        if not supported_files:
            return files

        def get_episode_info(fn: str) -> List[Optional[Union[int, str]]]:
            try:
                parsed: Any = PTN.parse(fn)
                episode_num: Optional[Union[int, str]] = parsed.get("episode")
                season_num: Optional[Union[int, str]] = parsed.get("season")
                year: Optional[Union[int, str]] = parsed.get("year")
                return [season_num, episode_num, year]
            except TypeError:
                return [None, None, None]

        def is_episode(fn: str) -> bool:
            extension: str = os.path.splitext(fn)[1][1:]
            if extension in settings.VIDEO_EXTENSIONS:
                _, episode_num, year = get_episode_info(fn)
                return bool(episode_num or year)
            return False

        if not any(list(map(is_episode, files))):
            return supported_files

        def get_episode_string(fn: str) -> str:
            extension: str = os.path.splitext(fn)[1][1:]
            if extension in settings.VIDEO_EXTENSIONS:
                season_num, episode_num, year = get_episode_info(fn)
                if episode_num and season_num:
                    return f"S{season_num:03}E{episode_num:03}"
                if episode_num:
                    return str(episode_num)
                if year:
                    return str(year)
            return ""

        if files:
            if not supported_files:
                return sorted(files)
            return sorted(supported_files, key=get_episode_string)
    return None


def _weighted_sort_date_seeds(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def getdate(d: Optional[datetime.datetime]) -> datetime.date:
        return d.date() if d else datetime.datetime.now().date()
    dates: List[datetime.date] = sorted([getdate(r.get("published")) for r in results])
    return sorted(results, key=lambda x: (1+dates.index(getdate(x.get("published")))) * x.get("seeds", 0) * (x.get("seeds",0) * 1.5), reverse=True)


@app.route("/robots.txt")
def robots() -> Response:
    return Response(
        """User-agent: *
Disallow: /""",
        mimetype="text/plain",
    )


def authorize(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def decorated_function(*args: Any, **kws: Any) -> Any:
        password: Optional[str] = request.cookies.get('password')
        if settings.PASSWORD and password != settings.PASSWORD:
            abort(404)
        return f(*args, **kws)
    return decorated_function


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def frontend(path: str) -> Response:
    if not path.startswith("index.html"):
        try:
            return send_from_directory("/app/frontend/", path)
        except NotFound:
            pass
    password: Optional[str] = request.cookies.get('password')
    if not settings.PASSWORD or password == settings.PASSWORD:
        return send_from_directory("/app/frontend/", "index.html", last_modified=datetime.datetime.now())
    return send_from_directory("/app/frontend/", "login.html", last_modified=datetime.datetime.now())


@app.route("/api", methods=["POST"])
def login() -> Response:
    password: Optional[str] = request.form.get("password")
    if not password:
        abort(404)
    response: Response = jsonify()
    if settings.PASSWORD and password == settings.PASSWORD:
        response.set_cookie('password', password)
    return response

@app.route("/api/search/", defaults={"searchterm": ""})
@app.route("/api/search/<string:searchterm>")
@authorize
def search(searchterm: str) -> Response:
    if settings.JACKETT_HOST:
        results: List[Dict[str, Any]] = jackett.search(searchterm)
    else:
        results = [
            {
                "title": "NO JACKETT SERVER CONFIGURED",
                "seeds": 1337,
                "magnet": "N/A"
            },
            {
                "title": "Please connect Jackett using the config variables JACKETT_HOST and JACKETT_API_KEY",
                "seeds": 1337,
                "magnet": "N/A"
            }
        ]
    filtered_results: List[Dict[str, Any]] = [r for r in results if not any(s in r.get("title","") for s in settings.MOVE_RESULTS_TO_BOTTOM_CONTAINING_STRINGS)]
    rest: List[Dict[str, Any]] = [r for r in results if any(s in r.get("title", "") for s in settings.MOVE_RESULTS_TO_BOTTOM_CONTAINING_STRINGS)]

    if searchterm == "":
        return jsonify(results=_weighted_sort_date_seeds(filtered_results) + rest)
    return jsonify(results=filtered_results + rest)


def _torrent_url_to_magnet(torrent_url: str) -> Optional[str]:
    filepath: str = "/tmp/" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + ".torrent"
    magnet_link: Optional[str] = None
    try:
        r: requests.Response = _session.get(torrent_url, allow_redirects=False, timeout=30)
        if r.status_code == 302:
            location: Optional[str] = r.headers.get("Location")
            if location and location.startswith("magnet"):
                return location
        with open(filepath, 'wb') as f:
            f.write(r.content)
        daemon.save_torrent_file(filepath)
        magnet_link = torrent.make_magnet_from_torrent_file(filepath)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(filepath)
    return magnet_link


@app.route("/api/torrent_url_to_magnet/", methods=["POST"])
@authorize
def torrent_url_to_magnet() -> Response:
    torrent_url: Optional[str] = request.form.get("url")
    magnet_link: Optional[str] = _torrent_url_to_magnet(torrent_url)  # type: ignore
    return jsonify(magnet_link=magnet_link)


@app.route("/api/magnet_files/", methods=["POST"])
@authorize
def magnet_info() -> Response:
    magnet_link: Optional[str] = request.form.get("magnet_link")
    magnet_hash: str = torrent.get_hash(magnet_link)  # type: ignore
    if not _get_files(magnet_hash):
        daemon.fetch_filelist_from_link(magnet_link)  # type: ignore
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet_download/", methods=["POST"])
@authorize
def magnet_download() -> Response:
    magnet_link: Optional[str] = request.form.get("magnet_link")
    filename: Optional[str] = request.form.get("filename")
    magnet_hash: str = torrent.get_hash(magnet_link)  # type: ignore
    if daemon.get_file_status(magnet_hash, filename)["status"] != FileStatus.READY:  # type: ignore
        daemon.download_file(magnet_link, filename)  # type: ignore
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet/<string:magnet_hash>/<string:filename>")
@authorize
def file_status(magnet_hash: str, filename: str) -> Response:
    return jsonify(**daemon.get_file_status(magnet_hash, filename))


@app.route("/api/next_file/<string:magnet_hash>/<string:filename>")
@authorize
def next_file(magnet_hash: str, filename: str) -> Response:
    next_filename: Optional[str] = None
    if settings.AUTO_PLAY_NEXT_FILE:
        files: Optional[List[str]] = _get_files(magnet_hash)
        if files:
            try:
                index: int = files.index(filename) + 1
                next_filename = files[index]
            except ValueError:
                pass
            except IndexError:
                pass
    return jsonify(next_filename=next_filename)


@app.route("/api/magnet/<string:magnet_hash>/")
@authorize
def files(magnet_hash: str) -> Response:
    files_list: Optional[List[str]] = _get_files(magnet_hash)

    if files_list:
        return jsonify(
            files=files_list
        )
    return jsonify(files=None)


@app.route("/error.log")
@authorize
def errorlog() -> Response:
    try:
        with open(settings.LOGFILE) as f:
            data: str = f.read()
    except OSError:
        data = ""
    return Response(data, mimetype="text/plain")


@app.route("/api/status")
@authorize
def status() -> Response:
    return jsonify(
        output_dir=path_hierarchy(settings.OUTPUT_DIR),
        filelist_dir=path_hierarchy(settings.FILELIST_DIR),
        torrents_dir=path_hierarchy(settings.TORRENTS_DIR),
        downloads_dir=path_hierarchy(settings.DOWNLOAD_DIR),
        subtitle_downloads=daemon.subtitle_downloads(),
        torrent_downloads=daemon.downloads(),
        session_torrents=daemon.session_torrents(),
        conversions=daemon.file_conversions(),
        http_downloads=daemon.http_downloads(),
    )


@app.route("/kodi.repo", defaults={"path": ""})
@app.route("/kodi.repo/", defaults={"path": ""})
@app.route("/kodi.repo/<string:path>")
def kodi_repo(path: str) -> Response:
    password: Optional[str] = request.authorization.password if request.authorization else None
    if not settings.PASSWORD or password == settings.PASSWORD:
        zip_filename: str = "rapidbay.zip"
        if path == zip_filename:
            creds: Dict[str, Optional[str]] = {"host": request.url_root.rstrip("/"), "password": settings.PASSWORD}
            with open("/app/kodi.addon/creds.json", "w") as f:
                json.dump(creds, f)
            filehash: str = (
                subprocess.Popen(
                    r"find /app/kodi.addon/ -type f -exec shasum {} \; | shasum | head -c 8",
                    stdout=subprocess.PIPE,
                    shell=True,
                )
                .stdout.read()  # type: ignore
                .decode()
            )
            filename: str = f"kodi_addon-{filehash}.zip"
            if not os.path.exists(f"/tmp/{filename}"):
                os.system(f"cd /app/; zip -r /tmp/{filename} kodi.addon")
            return send_from_directory(
                "/tmp/", filename, last_modified=datetime.datetime.now()
            )
        return Response(
            f"""<!DOCTYPE html>
        <a href="{zip_filename}">{zip_filename}</a>
        """,
            mimetype="text/html",
        )
    return Response(
        "Wrong password", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )
