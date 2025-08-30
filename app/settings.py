import os
from typing import List, Optional, Tuple

# RAPIDBAY
PASSWORD: Optional[str] = None
LOGFILE: str = "/tmp/rapidbay_errors.log"
AUTO_PLAY_NEXT_FILE: bool = True

# JACKETT
JACKETT_HOST: Optional[str] = None
JACKETT_API_KEY: str = ""

# TORRENT
TORRENT_LISTENING_PORT: Optional[int] = None
DOWNLOAD_DIR: str = "/tmp/downloads/"
FILELIST_DIR: str = "/tmp/filelists/"
TORRENTS_DIR: str = "/tmp/torrents/"
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
OUTPUT_DIR: str = "/tmp/output/"
AAC_BITRATE: str = "128k"
AAC_CHANNELS: int = 2
INCOMPLETE_POSTFIX: str = ".incomplete"
LOG_POSTFIX: str = ".log"
MAX_OUTPUT_FILE_AGE: int = 10  # hours
MAX_PARALLEL_CONVERSIONS: int = 2

OPENSUBTITLES_USERNAME: Optional[str] = None
OPENSUBTITLES_PASSWORD: Optional[str] = None

for variable in [item for item in globals() if not item.startswith("__")]:
    NULL = "NULL"
    env_var = os.getenv(variable, NULL)
    if env_var is not NULL:
        try:
            env_var = eval(env_var)
        except Exception:
            pass
    globals()[variable] = env_var if env_var is not NULL else globals()[variable]
