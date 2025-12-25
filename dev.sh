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
echo "Open http://localhost:5000 in your browser"
echo ""

uvicorn app:app --host 127.0.0.1 --port 5000 --reload --app-dir app
