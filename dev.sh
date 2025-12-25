#!/bin/bash
# Development mode runner - runs without nginx/docker

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export DEV_MODE=True

# Create data directories if they don't exist
mkdir -p ./data/{downloads,filelists,torrents,output,cache}

echo "Starting RapidBay in development mode..."
echo "Data directory: ./data"
echo ""

# Start daemon in background
echo "Starting daemon on port 5001..."
uvicorn rapidbaydaemon:app --host 127.0.0.1 --port 5001 --app-dir app &
DAEMON_PID=$!

# Give daemon time to start
sleep 2

# Start main app
echo "Starting main app on port 5000..."
echo "Open http://localhost:5000 in your browser"
echo ""
uvicorn app:app --host 127.0.0.1 --port 5000 --reload --app-dir app &
APP_PID=$!

# Handle shutdown
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $DAEMON_PID 2>/dev/null
    kill $APP_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
