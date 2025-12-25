import contextlib
import os
from typing import List, Optional, Tuple

# RAPIDBAY
PASSWORD: Optional[str] = None
AUTO_PLAY_NEXT_FILE: bool = True
DEV_MODE: bool = False  # Set to True to run without nginx/docker
DAEMON_PORT: int = 5001  # Port for daemon in dev mode

# PATHS - These are defaults, will be recomputed after env var loading
DATA_DIR: str = ""  # Base directory for all data (computed based on DEV_MODE)
CACHE_DIR: str = ""  # Cache directory
LOGFILE: str = ""
DOWNLOAD_DIR: str = ""
FILELIST_DIR: str = ""
TORRENTS_DIR: str = ""
OUTPUT_DIR: str = ""
FRONTEND_DIR: str = ""
KODI_ADDON_DIR: str = ""
DAEMON_SOCKET: str = ""

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
for variable in [item for item in globals() if not item.startswith("__")]:
    NULL = "NULL"
    env_var = os.getenv(variable, NULL)
    if env_var is not NULL:
        with contextlib.suppress(Exception):
            env_var = eval(env_var)
    globals()[variable] = env_var if env_var is not NULL else globals()[variable]


def _init_paths() -> None:
    """Initialize all paths based on DEV_MODE and DATA_DIR."""
    global DATA_DIR, CACHE_DIR, LOGFILE, DOWNLOAD_DIR, FILELIST_DIR
    global TORRENTS_DIR, OUTPUT_DIR, FRONTEND_DIR, KODI_ADDON_DIR, DAEMON_SOCKET

    # Set DATA_DIR if not already set via environment
    if not DATA_DIR:
        DATA_DIR = "./data" if DEV_MODE else "/tmp"

    # Derive all paths from DATA_DIR
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

    # App paths
    if not FRONTEND_DIR:
        FRONTEND_DIR = "./app/frontend" if DEV_MODE else "/app/frontend"
    if not KODI_ADDON_DIR:
        KODI_ADDON_DIR = "./app/kodi.addon" if DEV_MODE else "/app/kodi.addon"
    if not DAEMON_SOCKET:
        DAEMON_SOCKET = os.path.join(DATA_DIR, "rapidbaydaemon.sock") if DEV_MODE else "/app/rapidbaydaemon.sock"


_init_paths()
