import contextlib
import os
from typing import List, Optional, Tuple

# RAPIDBAY
PASSWORD: Optional[str] = None
AUTO_PLAY_NEXT_FILE: bool = True

# PATHS - Defaults for standalone, Docker overrides via env vars
DATA_DIR: str = "./data"
CACHE_DIR: str = ""
LOGFILE: str = ""
DOWNLOAD_DIR: str = ""
FILELIST_DIR: str = ""
TORRENTS_DIR: str = ""
OUTPUT_DIR: str = ""
FRONTEND_DIR: str = "./app/frontend"
KODI_ADDON_DIR: str = "./app/kodi.addon"

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

# Load environment variables
for _variable in [item for item in list(globals().keys()) if not item.startswith("_")]:
    _NULL = "NULL"
    _env_var = os.getenv(_variable, _NULL)
    if _env_var is not _NULL:
        with contextlib.suppress(Exception):
            _env_var = eval(_env_var)
        globals()[_variable] = _env_var

# Compute derived paths (if not explicitly set)
if not CACHE_DIR:
    CACHE_DIR = os.path.join(DATA_DIR, "cache")
if not LOGFILE:
    LOGFILE = os.path.join(DATA_DIR, "rapidbay_errors.log")
if not DOWNLOAD_DIR:
    DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads") + "/"
if not FILELIST_DIR:
    FILELIST_DIR = os.path.join(DATA_DIR, "filelists") + "/"
if not TORRENTS_DIR:
    TORRENTS_DIR = os.path.join(DATA_DIR, "torrents") + "/"
if not OUTPUT_DIR:
    OUTPUT_DIR = os.path.join(DATA_DIR, "output") + "/"
