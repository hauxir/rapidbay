import os
from urllib.parse import quote_plus, urlencode

import requests

from bs4 import BeautifulSoup
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from flask_basicauth import BasicAuth
from torrentclient import LOGFILE, TorrentClient

PIRATEBAY_HOST = "piratebay.live"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "123456"

tc = TorrentClient()
app = Flask(__name__)

basic_auth = BasicAuth(app)

app.config["BASIC_AUTH_USERNAME"] = os.environ.get("USERNAME", DEFAULT_USERNAME)
app.config["BASIC_AUTH_PASSWORD"] = os.environ.get("PASSWORD", DEFAULT_PASSWORD)


def search_piratebay(searchterm):
    magnet_links = []
    data = requests.get(f"https://{PIRATEBAY_HOST}/search/{searchterm}/1/7/0").text
    soup = BeautifulSoup(data, "html.parser")
    trs = soup.find(id="searchResult").find_all("tr")
    for tr in trs:
        try:
            td = tr.find_all("td")[1]
            seeds = int(tr.find_all("td")[2].contents[0])
            a = td.find_all("a")
            title = str(a[0].contents[0])
            magnet_link = a[1]["href"]
            if seeds:
                magnet_links.append(dict(title=title, magnet=magnet_link, seeds=seeds))
        except:
            pass
    return magnet_links


@app.route("/favicon.png")
def favicon():
    return send_from_directory("/app/", "favicon.png")


@app.route("/style.css")
def style():
    return send_from_directory("/app/", "style.css")


@app.route("/app.js")
def appjs():
    return send_from_directory("/app/", "app.js")


@app.route("/error.log")
def errorlog():
    with open(LOGFILE, "r") as f:
        data = f.read()
    return Response(data, mimetype="text/plain")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@basic_auth.required
def index(path):
    return send_from_directory("/app/", "index.html")


@app.route("/api/search/<string:searchterm>")
@basic_auth.required
def search(searchterm):
    return jsonify(results=search_piratebay(searchterm))


@app.route("/api/magnet_files/", methods=["POST"])
@basic_auth.required
def magnet_info():
    magnet_link = request.form.get("magnet_link")
    magnet_hash = tc.get_hash(magnet_link)
    tc.get_files_from_link(magnet_link)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet_download/", methods=["POST"])
@basic_auth.required
def magnet_download():
    magnet_link = request.form.get("magnet_link")
    filename = request.form.get("filename")
    magnet_hash = tc.get_hash(magnet_link)
    tc.download_file(magnet_link, filename)
    return jsonify(magnet_hash=magnet_hash)


@app.route("/api/magnet/<string:magnet_hash>/<string:filename>")
@basic_auth.required
def file_status(magnet_hash, filename):
    return jsonify(**tc.get_file_status(magnet_hash, filename))


@app.route("/api/magnet/<string:magnet_hash>/")
@basic_auth.required
def files(magnet_hash):
    return jsonify(files=tc.get_files(magnet_hash))


@app.route("/play/<string:magnet_hash>/<string:filename>")
def play(magnet_hash, filename):
    filename = filename.replace(".mkv", ".mp4")
    return send_from_directory(f"/tmp/output/{magnet_hash}", filename)


if __name__ == "__main__":
    tc.start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
