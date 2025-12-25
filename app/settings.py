import contextlib
import os
from typing import List, Optional, Tuple

# RAPIDBAY
PASSWORD: Optional[str] = None
AUTO_PLAY_NEXT_FILE: bool = True
STANDALONE: bool = False  # Set to True to run without Docker/nginx

# PATHS - Placeholder values, will be set after env var loading
_data_dir: str = ""
_cache_dir: str = ""
_logfile: str = ""
_download_dir: str = ""
_filelist_dir: str = ""
_torrents_dir: str = ""
_output_dir: str = ""
_frontend_dir: str = ""
_kodi_addon_dir: str = ""

# JACKETT
JACKETT_HOST: Optional[str] = None
JACKETT_API_KEY: str = ""

# TORRENT
TORRENT_LISTENING_PORT: Optional[int] = None
DHT_ROUTERS: List[Tuple[str, int]] = [
    ("router.utorrent.com", 6881),
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.bitcomet.com", 6881),
    ("dht.aelitis.com", 6881),
]
MAX_TORRENT_AGE_HOURS: int = 10
VIDEO_EXTENSIONS: List[str] = ["mp4", "mkv", "avi", "mpg", "mpeg"]
SUPPORTED_EXTENSIONS: List[str] = ["mp4", "mkv", "avi", "mpg", "mpeg", "mp3", "flac"]
TORRENT_DOWNLOAD_LIMIT: int = -1
TORRENT_UPLOAD_LIMIT: int = -1
EXCLUDE_TRACKERS_FROM_TRENDING: List[str] = []

MOVE_RESULTS_TO_BOTTOM_CONTAINING_STRINGS: List[str] = ["XviD"]

# SUBTITLES
SUBTITLE_LANGUAGES: List[str] = ["en"]  # list of languages, e.g. ["en", "de", "es"]

# CONVERSION
CONVERT_VIDEO: bool = True
VIDEO_CONVERSION_PARAMS: str = "libx264 -preset ultrafast"
AAC_BITRATE: str = "128k"
AAC_CHANNELS: int = 2
INCOMPLETE_POSTFIX: str = ".incomplete"
LOG_POSTFIX: str = ".log"
MAX_OUTPUT_FILE_AGE: int = 10  # hours
MAX_PARALLEL_CONVERSIONS: int = 2

OPENSUBTITLES_USERNAME: Optional[str] = None
OPENSUBTITLES_PASSWORD: Optional[str] = None

# Load environment variables (for non-path settings)
for _variable in [item for item in list(globals().keys()) if not item.startswith("_")]:
    _NULL = "NULL"
    _env_var = os.getenv(_variable, _NULL)
    if _env_var is not _NULL:
        with contextlib.suppress(Exception):
            _env_var = eval(_env_var)
        globals()[_variable] = _env_var

# Load path overrides from environment
_data_dir = os.getenv("DATA_DIR", "")
_cache_dir = os.getenv("CACHE_DIR", "")
_logfile = os.getenv("LOGFILE", "")
_download_dir = os.getenv("DOWNLOAD_DIR", "")
_filelist_dir = os.getenv("FILELIST_DIR", "")
_torrents_dir = os.getenv("TORRENTS_DIR", "")
_output_dir = os.getenv("OUTPUT_DIR", "")
_frontend_dir = os.getenv("FRONTEND_DIR", "")
_kodi_addon_dir = os.getenv("KODI_ADDON_DIR", "")

# Compute final path values (only assigned once)
DATA_DIR: str = _data_dir if _data_dir else ("./data" if STANDALONE else "/tmp")
CACHE_DIR: str = _cache_dir if _cache_dir else os.path.join(DATA_DIR, "cache")
LOGFILE: str = _logfile if _logfile else os.path.join(DATA_DIR, "rapidbay_errors.log")
DOWNLOAD_DIR: str = _download_dir if _download_dir else os.path.join(DATA_DIR, "downloads") + "/"
FILELIST_DIR: str = _filelist_dir if _filelist_dir else os.path.join(DATA_DIR, "filelists") + "/"
TORRENTS_DIR: str = _torrents_dir if _torrents_dir else os.path.join(DATA_DIR, "torrents") + "/"
OUTPUT_DIR: str = _output_dir if _output_dir else os.path.join(DATA_DIR, "output") + "/"
FRONTEND_DIR: str = _frontend_dir if _frontend_dir else ("./app/frontend" if STANDALONE else "/app/frontend")
KODI_ADDON_DIR: str = _kodi_addon_dir if _kodi_addon_dir else ("./app/kodi.addon" if STANDALONE else "/app/kodi.addon")
