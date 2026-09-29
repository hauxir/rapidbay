#!/bin/bash
# Run RapidBay (standalone or behind nginx)

# Create data directories if they don't exist
DATA_DIR="${DATA_DIR:-./data}"
LISTEN_PORT="${LISTEN_PORT:-5000}"
mkdir -p "$DATA_DIR"/{downloads,filelists,torrents,output,cache}

if [ "$USE_NGINX" = "1" ]; then
    # Docker mode: nginx reverse proxy + unix socket
    sed -i "s/\${LISTEN_PORT}/$LISTEN_PORT/g" /etc/nginx/conf.d/default.conf
    nginx
    exec uvicorn app:app --uds rapidbay.sock --workers 1 --timeout-keep-alive 900 --no-access-log
else
    # Standalone mode: direct HTTP
    echo "Starting RapidBay..."
    echo "Data directory: $DATA_DIR"
    echo "Open http://localhost:$LISTEN_PORT in your browser"
    echo ""
    exec uvicorn app:app --host 0.0.0.0 --port "$LISTEN_PORT" "$@"
fi
