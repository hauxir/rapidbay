import os

# RAPIDBAY
PASSWORD = None
LOGFILE = "/tmp/rapidbay_errors.log"
AUTO_PLAY_NEXT_FILE = True

# JACKETT
JACKETT_HOST = None
JACKETT_API_KEY = ""

# TORRENT
TORRENT_LISTENING_PORT = None
DOWNLOAD_DIR = "/tmp/downloads/"
FILELIST_DIR = "/tmp/filelists/"
TORRENTS_DIR = "/tmp/torrents/"
DHT_ROUTERS = [
    ("router.utorrent.com", 6881),
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.bitcomet.com", 6881),
    ("dht.aelitis.com", 6881),
]
MAX_TORRENT_AGE_HOURS = 10
VIDEO_EXTENSIONS = ["mp4", "mkv", "avi", "mpg", "mpeg"]
SUPPORTED_EXTENSIONS = ["mp4", "mkv", "avi", "mpg", "mpeg", "mp3", "flac"]
TORRENT_DOWNLOAD_LIMIT = -1
TORRENT_UPLOAD_LIMIT = -1

# SUBTITLES
SUBTITLE_LANGUAGES = ["en"]  # list of languages, e.g. ["en", "de", "es"]

# CONVERSION
CONVERT_VIDEO = True
OUTPUT_DIR = "/tmp/output/"
AAC_BITRATE = "128k"
AAC_CHANNELS = 2
INCOMPLETE_POSTFIX = ".incomplete"
LOG_POSTFIX = ".log"
MAX_OUTPUT_FILE_AGE = 10 # hours
MAX_PARALLEL_CONVERSIONS = 2

OPENSUBTITLES_USERNAME = None
OPENSUBTITLES_PASSWORD = None

for variable in [item for item in globals() if not item.startswith("__")]:
    NULL = "NULL"
    env_var = os.getenv(variable, NULL)
    if env_var is not NULL:
        try:
            env_var = eval(env_var)
        except Exception:
            pass
    globals()[variable] = env_var if env_var is not NULL else globals()[variable]
