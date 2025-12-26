import contextlib
import datetime
import json
import os
import random
import shlex
import string
import subprocess
import urllib.parse
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator, Dict, List, Optional, Union

import http_cache
import jackett
import PTN
import requests
import settings
import torrent
from common import path_hierarchy
from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from rapidbaydaemon import FileStatus, RapidBayDaemon, get_filepaths
from starlette.middleware.base import BaseHTTPMiddleware


# Response models for OpenAPI schema
class SearchResult(BaseModel):
    title: str
    seeds: int
    magnet: str


class SearchResponse(BaseModel):
    results: List[SearchResult]


class MagnetLinkResponse(BaseModel):
    magnet_link: Optional[str]


class MagnetHashResponse(BaseModel):
    magnet_hash: str


class FileStatusResponse(BaseModel):
    status: str
    filename: Optional[str] = None
    subtitles: Optional[List[str]] = None
    supported: Optional[bool] = None
    progress: Optional[float] = None
    peers: Optional[int] = None


class NextFileResponse(BaseModel):
    next_filename: Optional[str]


class FilesResponse(BaseModel):
    files: Optional[List[str]]


class StatusResponse(BaseModel):
    output_dir: Any
    filelist_dir: Any
    torrents_dir: Any
    downloads_dir: Any
    subtitle_downloads: Any
    torrent_downloads: Any
    session_torrents: List[str]
    conversions: Any
    http_downloads: Any

# Global daemon instance
daemon: RapidBayDaemon


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global daemon
    daemon = RapidBayDaemon()
    daemon.start()
    try:
        yield
    finally:
        daemon.stop()


app: FastAPI = FastAPI(lifespan=lifespan, openapi_url=None)


@app.get("/openapi.json", include_in_schema=False)
def custom_openapi(request: Request) -> Dict[str, Any]:
    from fastapi.openapi.utils import get_openapi

    host = settings.OPENAPI_HOST or str(request.base_url).rstrip("/")
    return get_openapi(
        title="RapidBay",
        version="1.0.0",
        routes=app.routes,
        servers=[{"url": host, "description": "RapidBay API"}],
    )


class HeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:  # type: ignore[override]
        response: Response = await call_next(request)
        # Move set-cookie header to x-set-cookie header
        set_cookie = response.headers.get("set-cookie")
        if set_cookie:
            response.headers["x-set-cookie"] = set_cookie
        # Convert X-Sendfile to X-Accel-Redirect for Nginx (harmless if nginx not present)
        x_sendfile: Optional[str] = response.headers.get("X-Sendfile")
        if x_sendfile:
            response.headers["X-Accel-Redirect"] = urllib.parse.quote(f"/nginx/{x_sendfile}")
            del response.headers["X-Sendfile"]
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        return response


app.add_middleware(HeaderMiddleware)


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


@app.get("/robots.txt")
def robots() -> PlainTextResponse:
    return PlainTextResponse(
        """User-agent: *
Disallow: /""",
    )


bearer_scheme = HTTPBearer(auto_error=False)


def authorize(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    password: Annotated[Optional[str], Cookie(include_in_schema=False)] = None,
) -> None:
    if not settings.PASSWORD:
        return
    # Check Bearer token first
    if credentials and credentials.credentials == settings.PASSWORD:
        return
    # Fall back to cookie
    if password == settings.PASSWORD:
        return
    raise HTTPException(status_code=404)


def _send_from_directory(directory: str, filename: str, last_modified: Optional[datetime.datetime] = None) -> FileResponse:
    filepath = os.path.join(directory, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    headers: Dict[str, str] = {}
    if last_modified:
        headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return FileResponse(filepath, headers=headers)


@app.post("/api")
def login(password: Optional[str] = Form(default=None)) -> Response:
    if not password:
        raise HTTPException(status_code=404)
    response = Response(content="{}", media_type="application/json")
    if settings.PASSWORD and password == settings.PASSWORD:
        response.set_cookie(key='password', value=password)
    return response


@app.get("/api/search/", response_model=SearchResponse)
@app.get("/api/search/{searchterm}", response_model=SearchResponse)
def search(searchterm: str = "", _: None = Depends(authorize)) -> Dict[str, Any]:
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
        return {"results": _weighted_sort_date_seeds(filtered_results) + rest}
    return {"results": filtered_results + rest}


def _torrent_url_to_magnet(torrent_url: str) -> Optional[str]:
    filepath: str = os.path.join(settings.DATA_DIR, ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)) + ".torrent")
    magnet_link: Optional[str] = None
    try:
        r: requests.Response = requests.get(torrent_url, allow_redirects=False, timeout=30)
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


@app.post("/api/torrent_url_to_magnet/", response_model=MagnetLinkResponse)
def torrent_url_to_magnet(url: Optional[str] = Form(default=None), _: None = Depends(authorize)) -> Dict[str, Any]:
    magnet_link: Optional[str] = _torrent_url_to_magnet(url)  # type: ignore
    return {"magnet_link": magnet_link}


@app.post("/api/magnet_files/", response_model=MagnetHashResponse)
def magnet_info(magnet_link: Optional[str] = Form(default=None), _: None = Depends(authorize)) -> Dict[str, str]:
    magnet_hash: str = torrent.get_hash(magnet_link)  # type: ignore
    if not _get_files(magnet_hash):
        daemon.fetch_filelist_from_link(magnet_link)
    return {"magnet_hash": magnet_hash}


@app.post("/api/magnet_download/", response_model=MagnetHashResponse)
def magnet_download(
    magnet_link: Optional[str] = Form(default=None),
    filename: Optional[str] = Form(default=None),
    _: None = Depends(authorize)
) -> Dict[str, str]:
    if not magnet_link or not filename:
        raise HTTPException(status_code=400, detail="magnet_link and filename required")
    magnet_hash: str = torrent.get_hash(magnet_link)
    if daemon.get_file_status(magnet_hash, filename)["status"] != FileStatus.READY:
        daemon.download_file(magnet_link, filename)
    return {"magnet_hash": magnet_hash}


@app.get("/api/magnet/{magnet_hash}/{filename}", response_model=FileStatusResponse)
def file_status(magnet_hash: str, filename: str, _: None = Depends(authorize)) -> Dict[str, Any]:
    return daemon.get_file_status(magnet_hash, filename)


@app.get("/api/next_file/{magnet_hash}/{filename}", response_model=NextFileResponse)
def next_file(magnet_hash: str, filename: str, _: None = Depends(authorize)) -> Dict[str, Optional[str]]:
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
    return {"next_filename": next_filename}


@app.get("/api/magnet/{magnet_hash}/", response_model=FilesResponse)
def files(magnet_hash: str, _: None = Depends(authorize)) -> Dict[str, Optional[List[str]]]:
    files_list: Optional[List[str]] = _get_files(magnet_hash)

    if files_list:
        return {"files": files_list}
    return {"files": None}


@app.get("/error.log")
def errorlog(_: None = Depends(authorize)) -> PlainTextResponse:
    try:
        with open(settings.LOGFILE) as f:
            data: str = f.read()
    except OSError:
        data = ""
    return PlainTextResponse(data)


@app.get("/api/status", response_model=StatusResponse)
def status(_: None = Depends(authorize)) -> Dict[str, Any]:
    return {
        "output_dir": path_hierarchy(settings.OUTPUT_DIR),
        "filelist_dir": path_hierarchy(settings.FILELIST_DIR),
        "torrents_dir": path_hierarchy(settings.TORRENTS_DIR),
        "downloads_dir": path_hierarchy(settings.DOWNLOAD_DIR),
        "subtitle_downloads": daemon.subtitle_downloads,
        "torrent_downloads": daemon.downloads(),
        "session_torrents": daemon.session_torrents(),
        "conversions": daemon.video_converter.file_conversions,
        "http_downloads": daemon.http_downloader.downloads,
    }


@app.get("/kodi.repo")
@app.get("/kodi.repo/")
@app.get("/kodi.repo/{path}")
def kodi_repo(request: Request, path: str = "") -> Response:
    # Extract basic auth password
    password: Optional[str] = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        import base64
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            if ":" in decoded:
                password = decoded.split(":", 1)[1]
        except (ValueError, UnicodeDecodeError):
            pass  # Invalid base64 or encoding - treat as no auth

    if not settings.PASSWORD or password == settings.PASSWORD:
        zip_filename: str = "rapidbay.zip"
        if path == zip_filename:
            creds: Dict[str, Optional[str]] = {"host": str(request.base_url).rstrip("/"), "password": settings.PASSWORD}
            creds_file = os.path.join(settings.KODI_ADDON_DIR, "creds.json")
            with open(creds_file, "w") as f:
                json.dump(creds, f)
            filehash: str = (
                subprocess.Popen(
                    f"find {shlex.quote(settings.KODI_ADDON_DIR)} -type f -exec shasum {{}} \\; | shasum | head -c 8",
                    stdout=subprocess.PIPE,
                    shell=True,
                )
                .stdout.read()  # type: ignore
                .decode()
            )
            filename: str = f"kodi_addon-{filehash}.zip"
            zip_path = os.path.join(settings.DATA_DIR, filename)
            if not os.path.exists(zip_path):
                kodi_parent = os.path.dirname(settings.KODI_ADDON_DIR)
                kodi_name = os.path.basename(settings.KODI_ADDON_DIR)
                os.system(f"cd {shlex.quote(kodi_parent)}; zip -r {shlex.quote(zip_path)} {shlex.quote(kodi_name)}")
            return _send_from_directory(settings.DATA_DIR, filename, last_modified=datetime.datetime.now())
        return HTMLResponse(
            f"""<!DOCTYPE html>
        <a href="{zip_filename}">{zip_filename}</a>
        """,
        )
    return Response(
        content="Wrong password",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Login Required"'}
    )


@app.get("/play/{magnet_hash}/{filename:path}")
def play(magnet_hash: str, filename: str, _: None = Depends(authorize)) -> Response:
    directory = os.path.realpath(os.path.join(settings.OUTPUT_DIR, magnet_hash))
    filepath = os.path.realpath(os.path.join(directory, filename))
    if not filepath.startswith(directory + os.sep):
        raise HTTPException(status_code=404, detail="File not found")
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    response = FileResponse(filepath)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Catch-all route for frontend - MUST be defined last
@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str, password: Optional[str] = Cookie(default=None)) -> Response:
    if path == "":
        path = "index.html"
    if not path.startswith("index.html"):
        filepath = os.path.join(settings.FRONTEND_DIR, path)
        if os.path.isfile(filepath):
            return FileResponse(filepath)
    if not settings.PASSWORD or password == settings.PASSWORD:
        return _send_from_directory(settings.FRONTEND_DIR, "index.html", last_modified=datetime.datetime.now())
    return _send_from_directory(settings.FRONTEND_DIR, "login.html", last_modified=datetime.datetime.now())
