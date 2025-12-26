#!/bin/bash
# Run RapidBay (standalone or behind nginx)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create data directories if they don't exist
DATA_DIR="${DATA_DIR:-./data}"
mkdir -p "$DATA_DIR"/{downloads,filelists,torrents,output,cache}

if [ "$USE_NGINX" = "1" ]; then
    # Docker mode: nginx reverse proxy + unix socket
    nginx
    exec uvicorn app:app --uds rapidbay.sock --workers 1 --timeout-keep-alive 900 --app-dir app
else
    # Standalone mode: direct HTTP
    echo "Starting RapidBay..."
    echo "Data directory: $DATA_DIR"
    echo "Open http://localhost:5000 in your browser"
    echo ""
    exec uvicorn app:app --host 0.0.0.0 --port 5000 --app-dir app "$@"
fi
