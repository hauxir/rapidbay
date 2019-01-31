import json
import os

import piratebay
import settings
import torrent
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_basicauth import BasicAuth
from rapidbaydaemon import RapidBayDaemon
from werkzeug.exceptions import NotFound

daemon = RapidBayDaemon()
app = Flask(__name__)

basic_auth = BasicAuth(app)

app.config["BASIC_AUTH_USERNAME"] = settings.USERNAME
app.config["BASIC_AUTH_PASSWORD"] = settings.PASSWORD


def _get_files(magnet_hash):
    filename = os.path.join(settings.FILELIST_DIR, magnet_hash)
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            data = f.read().replace("\n", "")
            return json.loads(data)
    return None


@app.route("/robots.txt")
def robots():
    return Response(
        """User-agent: *
Disallow: /""",
        mimetype="text/plain",
    )


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@basic_auth.required
def frontend(path):
    try:
        return send_from_directory("/app/frontend/", path)
    except NotFound:
        pass
    return send_from_directory("/app/frontend/", "index.html")


@app.route("/api/search/<string:searchterm>")
@basic_auth.required
def search(searchterm):
    return jsonify(results=piratebay.search(searchterm))


@app.route("/api/magnet_files/", methods=["POST"])
@basic_auth.required
def magnet_info():
    magnet_link = request.form.get("magnet_link")
    magnet_hash = torrent.get_hash(magnet_link)
    daemon.fetch_filelist_from_link(magnet_link)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet_download/", methods=["POST"])
@basic_auth.required
def magnet_download():
    magnet_link = request.form.get("magnet_link")
    filename = request.form.get("filename")
    magnet_hash = torrent.get_hash(magnet_link)
    daemon.download_file(magnet_link, filename)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet/<string:magnet_hash>/<string:filename>")
@basic_auth.required
def file_status(magnet_hash, filename):
    return jsonify(**daemon.get_file_status(magnet_hash, filename))


@app.route("/api/magnet/<string:magnet_hash>/")
@basic_auth.required
def files(magnet_hash):
    files = _get_files(magnet_hash)
    if files:
        return jsonify(
            files=[
                f
                for f in files
                if any(f.endswith(f".{ext}") for ext in settings.SUPPORTED_EXTENSIONS)
            ]
        )
    return jsonify(files=None)


@app.route("/play/<string:magnet_hash>/<string:filename>")
def play(magnet_hash, filename):
    response = send_from_directory(f"/tmp/output/{magnet_hash}", filename)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/error.log")
def errorlog():
    try:
        with open(settings.LOGFILE, "r") as f:
            data = f.read()
    except IOError:
        data = ""
    return Response(data, mimetype="text/plain")


if __name__ == "__main__":
    daemon.start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
