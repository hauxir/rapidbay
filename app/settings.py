import os

# RAPIDBAY
USERNAME = "admin"
PASSWORD = "123456"
LOGFILE = "/tmp/rapidbay_errors.log"

# PIRATEBAY
PIRATEBAY_HOST = "piratebay.live"

# TORRENT
TORRENT_LISTENING_PORT = 6881
DOWNLOAD_DIR = "/tmp/downloads/"
FILELIST_DIR = "/tmp/filelists/"
DHT_ROUTERS = [
    ("router.utorrent.com", 6881),
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.bitcomet.com", 6881),
    ("dht.aelitis.com", 6881),
]
MAX_TORRENT_AGE_HOURS = 10
VIDEO_EXTENSIONS = ["mp4", "mkv"]
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS + ["mp3", "flac"]
TORRENT_DOWNLOAD_LIMIT = -1
TORRENT_UPLOAD_LIMIT = -1

# CONVERSION
OUTPUT_DIR = "/tmp/output/"
AAC_BITRATE = "128k"
AAC_CHANNELS = 2
INCOMPLETE_POSTFIX = ".incomplete"
LOG_POSTFIX = ".log"
MAX_OUTPUT_FILE_AGE = 10
MAX_PARALLEL_CONVERSIONS = 2

for variable in [item for item in globals() if not item.startswith("__")]:
    NULL = "NULL"
    env_var = os.getenv(variable, NULL)
    if env_var is not NULL:
        try:
            env_var = eval(env_var)
        except Exception:
            pass
    globals()[variable] = env_var if env_var is not NULL else globals()[variable]
