import datetime
import asyncio
import json
import os
import string
import random
import requests
import PTN
from functools import wraps

import jackett
import settings
import torrent
from common import path_hierarchy
from flask import Flask, Response, jsonify, request, send_from_directory, abort
from rapidbaydaemon import FileStatus, RapidBayDaemon
from werkzeug.exceptions import NotFound

daemon = RapidBayDaemon()
app = Flask(__name__)


@app.after_request
def add_header(response):
    response.headers["x-set-cookie"] = response.headers.get("set-cookie")
    return response


def _get_files(magnet_hash):
    filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            data = f.read().replace("\n", "")
            files = json.loads(data)
            supported_files = [
                f
                for f in files
                if any(f.endswith(f".{ext}") for ext in settings.SUPPORTED_EXTENSIONS)
            ]

            def get_episode_info(fn):
                parsed = PTN.parse(fn)
                episode_num = parsed.get("episode")
                season_num = parsed.get("season")
                year = parsed.get("year")
                return [season_num, episode_num, year]

            def is_episode(fn):
                extension = os.path.splitext(fn)[1][1:]
                if extension in settings.VIDEO_EXTENSIONS:
                    [season_num, episode_num, year] = get_episode_info(fn)
                    return bool(episode_num or year)
                return False

            if not any(list(map(is_episode, files))):
                return supported_files

            def get_episode_string(fn):
                extension = os.path.splitext(fn)[1][1:]
                if extension in settings.VIDEO_EXTENSIONS:
                    [season_num, episode_num, year] = get_episode_info(fn)
                    if episode_num and season_num:
                        return f"S{season_num:03}E{episode_num:03}"
                    if episode_num:
                        return str(episode_num)
                    if year:
                        return str(year)
                return ""

            if files:
                return sorted(supported_files, key=get_episode_string)
        return None


def _weighted_sort_date_seeds(results):
    getdate = lambda d: d.date() if d else datetime.datetime.now().date()
    dates = sorted([getdate(r.get("published")) for r in results])
    return sorted(results, key=lambda x: dates.index(getdate(x.get("published"))) * x.get("seeds", 0), reverse=True)


@app.route("/robots.txt")
def robots():
    return Response(
        """User-agent: *
Disallow: /""",
        mimetype="text/plain",
    )


def authorize(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        password = request.cookies.get('password')
        if settings.PASSWORD and password != settings.PASSWORD:
            abort(404)
        return f(*args, **kws)
    return decorated_function


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def frontend(path):
    if not path.startswith("index.html"):
        try:
            return send_from_directory("/app/frontend/", path)
        except NotFound:
            pass
    password = request.cookies.get('password')
    if not settings.PASSWORD or password == settings.PASSWORD:
        return send_from_directory("/app/frontend/", "index.html", last_modified=datetime.datetime.now())
    return send_from_directory("/app/frontend/", "login.html", last_modified=datetime.datetime.now())


@app.route("/api", methods=["POST"])
def login():
    password = request.form.get("password")
    if not password:
        abort(404)
    response = jsonify()
    if settings.PASSWORD and password == settings.PASSWORD:
        response.set_cookie('password', password)
    return response


@app.route("/api/search/", defaults=dict(searchterm=""))
@app.route("/api/search/<string:searchterm>")
@authorize
def search(searchterm):
    if settings.JACKETT_HOST:
        results = jackett.search(searchterm)
    else:
        results = [
            dict(
                title="NO JACKETT SERVER CONFIGURED",
                seeds=1337,
                magnet="N/A"
            ),
            dict(
                title="Please connect Jackett using the config variables JACKETT_HOST and JACKETT_API_KEY",
                seeds=1337,
                magnet="N/A"
            )
        ]

    if searchterm == "":
        return jsonify(results=_weighted_sort_date_seeds(results))


    return jsonify(results=sorted(results, key=lambda x: x["seeds"], reverse=True))


@app.route("/api/torrent_url_to_magnet/", methods=["POST"])
@authorize
def torrent_url_to_magnet():
    torrent_url = request.form.get("url")
    filepath = "/tmp/" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + ".torrent"
    magnet_link = None
    try:
        r = requests.get(torrent_url, allow_redirects=False)
        if r.status_code == 302:
            location = r.headers.get("Location")
            if location and location.startswith("magnet"):
                return jsonify(magnet_link=location)
        with open(filepath, 'wb') as f:
            f.write(r.content)
        daemon.save_torrent_file(filepath)
        magnet_link = torrent.make_magnet_from_torrent_file(filepath)
    finally:
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
    return jsonify(magnet_link=magnet_link)


@app.route("/api/magnet_files/", methods=["POST"])
@authorize
def magnet_info():
    magnet_link = request.form.get("magnet_link")
    magnet_hash = torrent.get_hash(magnet_link)
    if not _get_files(magnet_hash):
        daemon.fetch_filelist_from_link(magnet_link)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet_download/", methods=["POST"])
@authorize
def magnet_download():
    magnet_link = request.form.get("magnet_link")
    filename = request.form.get("filename")
    magnet_hash = torrent.get_hash(magnet_link)
    if daemon.get_file_status(magnet_hash, filename)["status"] != FileStatus.READY:
        daemon.download_file(magnet_link, filename)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet/<string:magnet_hash>/<string:filename>")
@authorize
def file_status(magnet_hash, filename):
    return jsonify(**daemon.get_file_status(magnet_hash, filename))


@app.route("/api/next_file/<string:magnet_hash>/<string:filename>")
@authorize
def next_file(magnet_hash, filename):
    next_filename = None
    if settings.AUTO_PLAY_NEXT_FILE:
        files = _get_files(magnet_hash)
        if files:
            try:
                index = files.index(filename) + 1
                next_filename = files[index]
            except ValueError:
                pass
            except IndexError:
                pass
    return jsonify(next_filename=next_filename)


@app.route("/api/magnet/<string:magnet_hash>/")
@authorize
def files(magnet_hash):
    files = _get_files(magnet_hash)

    if files:
        return jsonify(
            files=files
        )
    return jsonify(files=None)


@app.route("/play/<string:magnet_hash>/<string:filename>")
def play(magnet_hash, filename):
    response = send_from_directory(f"/tmp/output/{magnet_hash}", filename)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/error.log")
@authorize
def errorlog():
    try:
        with open(settings.LOGFILE, "r") as f:
            data = f.read()
    except IOError:
        data = ""
    return Response(data, mimetype="text/plain")


@app.route("/status")
@authorize
def status():
    return jsonify(
        output_dir=path_hierarchy(settings.OUTPUT_DIR),
        filelist_dir=path_hierarchy(settings.FILELIST_DIR),
        torrents_dir=path_hierarchy(settings.TORRENTS_DIR),
        downloads_dir=path_hierarchy(settings.DOWNLOAD_DIR),
        subtitle_downloads=daemon.subtitle_downloads,
        torrent_downloads=daemon.downloads(),
        session_torrents=daemon.session_torrents(),
        conversions=daemon.video_converter.file_conversions,
    )


if __name__ == "__main__":
    daemon.start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
