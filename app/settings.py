# RAPIDBAY
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "123456"
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
SUPPORTED_EXTENSIONS = ["mp4", "mkv"]

# CONVERSION
OUTPUT_DIR = "/tmp/output/"
AAC_BITRATE = "128k"
INCOMPLETE_POSTFIX = ".incomplete.mp4"
LOG_POSTFIX = ".log"
MAX_OUTPUT_FILE_AGE = 10
MAX_PARALLEL_CONVERSIONS = 2
