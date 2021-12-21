import datetime
import asyncio
import json
import os
import string
import random
import requests
import subprocess
import PTN
from functools import wraps

import jackett
import settings
import torrent
from common import path_hierarchy
from flask import Flask, Response, jsonify, request, send_from_directory, abort
from rapidbaydaemon import FileStatus, RapidBayDaemon, get_filepaths
from werkzeug.exceptions import NotFound

daemon = RapidBayDaemon()
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


@app.after_request
def add_header(response):
    response.headers["x-set-cookie"] = response.headers.get("set-cookie")
    return response


def _get_files(magnet_hash):
    """
    Get a list of files from the magnet hash.

    :param str magnet_hash: The
    magnet hash to get the filepaths for.
    :returns: A list of supported files
    or None if no supported files were found.
    """
    filepaths = get_filepaths(magnet_hash)
    if filepaths:
        files = [os.path.basename(f) for f in filepaths]
        supported_files = [
            f
            for f in files
            if any(f.endswith(f".{ext}") for ext in settings.SUPPORTED_EXTENSIONS)
        ]

        def get_episode_info(fn):
            """
            Parses a filename for season and episode numbers.

            :param fn: The filename
            to parse.
            :type fn: str
            """
            try:
                parsed = PTN.parse(fn)
                episode_num = parsed.get("episode")
                season_num = parsed.get("season")
                year = parsed.get("year")
                return [season_num, episode_num, year]
            except TypeError:
                return [None,None,None]

        def is_episode(fn):
            """
            Returns True if the filename is an episode, False otherwise.

            An episode is
            defined as a file with one of the extensions in
            :data:`VIDEO_EXTENSIONS`.
            If it has either season or episode numbers,
            then they must be present and
            consistent with each other.

            Parameters
                fn (str): The filename to check
            for being an episode.

                settings (:class:`~settings.Settings`,
            optional): A Settings object that contains information about how to rename
            files and what actions to take on them; default ``None`` which uses
            :attr:`settings`.  # noqaroparam settings=None) -> NoneType[edit]
            .. note :: This parameter should only be used internally by this function;
            all other code should use :attr:`settings`.  # noqatag internal) ->
            NoneType[edit]

                    .. warning :: Passing this argument is not secure
            if the source code of this function can be modified by an outsider; make
            sure you do not let anyone else have access to your source code!  # noqatag
            security) -> NoneType[edit]
            """
            extension = os.path.splitext(fn)[1][1:]
            if extension in settings.VIDEO_EXTENSIONS:
                [season_num, episode_num, year] = get_episode_info(fn)
                return bool(episode_num or year)
            return False

        if not any(list(map(is_episode, files))):
            return supported_files

        def get_episode_string(fn):
            """
            Given a filename, return the episode string for that file.

            Parameters:
            fn (str): The filename to get the episode string from.

                Returns: str or
            NoneType: The episode string for this file if it is an video file,
            otherwise None.
            """
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
    """
    Sorts a list of dictionaries by the value of their "seeds" key, then by the
    date they were published.
    If two items have equal seeds, they are sorted by
    date.
    """
    getdate = lambda d: d.date() if d else datetime.datetime.now().date()
    dates = sorted([getdate(r.get("published")) for r in results])
    return sorted(results, key=lambda x: (1+dates.index(getdate(x.get("published")))) * x.get("seeds", 0), reverse=True)


@app.route("/robots.txt")
def robots():
    return Response(
        """User-agent: *
Disallow: /""",
        mimetype="text/plain",
    )


def authorize(f):
    """
    Decorator that checks if the user is authorized to view the page.
    """
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
    """
    If the path is not index.html, try to send it from the frontend directory.
    Otherwise, if there's a password set and it matches what's in the cookie,
    return index.html from the frontend directory.
    Otherwise return login.html
    from the frontend directory.
    """
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
    """
    .. function: login
        Logs in the user by setting a cookie with the
    password.

        :param str password: The user's password.
    """
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
    """
    Searches for torrents using Jackett.

    :param searchterm: The string to
    search for.
    :type searchterm: str

        :returns results_list: A list of
    dicts containing the keys 'title', 'seeds' and 'magnet'.
        :rtype
    results_list: list[dict]

            **Example**

            .. code-block ::
    json

                {results=[{'title': "The Flash", seeds=1337,
    magnet="N/A"}, {...}, ...]} # List of dicts with title, seeds and magnet
    link as keys.
    """
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
    filtered_results = [r for r in results if not any(s in r.get("title","") for s in settings.MOVE_RESULTS_TO_BOTTOM_CONTAINING_STRINGS)]
    rest = [r for r in results if any(s in r.get("title", "") for s in settings.MOVE_RESULTS_TO_BOTTOM_CONTAINING_STRINGS)]

    if searchterm == "":
        return jsonify(results=_weighted_sort_date_seeds(filtered_results) + rest)
    return jsonify(results=filtered_results + rest)


@app.route("/api/torrent_url_to_magnet/", methods=["POST"])
@authorize
def torrent_url_to_magnet():
    """
    Convert a torrent URL to a magnet link.

    :param str url: The URL of the
    torrent file.
    """
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
    """
    .. function: magnet_info()
        :returns: jsonified magnet hash

        This
    function is used to get the hash of a torrent file from its magnet link.
    """
    magnet_link = request.form.get("magnet_link")
    magnet_hash = torrent.get_hash(magnet_link)
    if not _get_files(magnet_hash):
        daemon.fetch_filelist_from_link(magnet_link)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet_download/", methods=["POST"])
@authorize
def magnet_download():
    """
    Download a file from a magnet link.

    :param str magnet_link: The URL of the
    magnet link to download.
    :param str filename: The name of the file to save
    as. If not provided, it will be generated from the hash and extension in
    the torrent metadata.
    """
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
    """
    Returns the next file in a magnet link's directory.

    :param str
    magnet_hash: The hash of the magnet link.
    :param str filename: The name of
    the current file being played.
    """
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
    """
    Serves the video file with the given filename from a directory named after
    its magnet hash.
    """
    response = send_from_directory(f"/tmp/output/{magnet_hash}", filename)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/error.log")
@authorize
def errorlog():
    """
    Returns the contents of the logfile.

    :returns: The contents of the logfile
    as a plain text file.
    """
    try:
        with open(settings.LOGFILE, "r") as f:
            data = f.read()
    except IOError:
        data = ""
    return Response(data, mimetype="text/plain")


@app.route("/status")
@authorize
def status():
    """
    Get status of the daemon.

    Returns:
        dict: A dictionary containing
    information about the current state of the daemon. The keys are as follows:
    * **output_dir** (str): The path to where output files are stored,
    including subtitles and torrents. This is read from
    ``settings['OUTPUT_DIR']``.

            * **filelist_dir** (str): The path to
    where filelists for torrents are stored, which includes a list of all files
    in each torrent and their metadata such as title and description. This is
    read from ``settings['FILELIST_DIR']``

            * **torrents_dir** (str):
    The path to where .torrent files for each download are stored, ready to be
    added by rTorrent or Deluge when they're downloaded next time around using
    :func:`~flexget.plugins.daemonized._plugin._add`. This is read from
    ``settings['TORRENTS_DIR']``

            * **downloads_dir** (str): Path that
    downloads end up at on this machine after being finished downloading via
    rTorrent or Deluge; this should match your settings in those clients so
    they know where things go! It's
    """
    return jsonify(
        output_dir=path_hierarchy(settings.OUTPUT_DIR),
        filelist_dir=path_hierarchy(settings.FILELIST_DIR),
        torrents_dir=path_hierarchy(settings.TORRENTS_DIR),
        downloads_dir=path_hierarchy(settings.DOWNLOAD_DIR),
        subtitle_downloads=daemon.subtitle_downloads,
        torrent_downloads=daemon.downloads(),
        session_torrents=daemon.session_torrents(),
        conversions=daemon.video_converter.file_conversions,
        http_downloads=daemon.http_downloader.downloads,
    )


@app.route("/kodi.repo", defaults={"path": ""})
@app.route("/kodi.repo/", defaults={"path": ""})
@app.route("/kodi.repo/<string:path>")
def kodi_repo(path):
    """
    Returns a Kodi addon repository zip file.

    :param path: The URL path of the
    request.
    """
    password = request.authorization.password if request.authorization else None
    if not settings.PASSWORD or password == settings.PASSWORD:
        zip_filename = "rapidbay.zip"
        if path == zip_filename:
            creds = dict(host=request.url_root.rstrip("/"), password=settings.PASSWORD)
            with open("/app/kodi.addon/creds.json", "w") as f:
                json.dump(creds, f)
            filehash = (
                subprocess.Popen(
                    "find /app/kodi.addon/ -type f -exec shasum {} \; | shasum | head -c 8",
                    stdout=subprocess.PIPE,
                    shell=True,
                )
                .stdout.read()
                .decode()
            )
            filename = f"kodi_addon-{filehash}.zip"
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


if __name__ == "__main__":
    daemon.start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
