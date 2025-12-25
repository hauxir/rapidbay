#!/bin/bash
# Run RapidBay (standalone or behind nginx)

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create data directories if they don't exist
mkdir -p ./data/{downloads,filelists,torrents,output,cache}

echo "Starting RapidBay..."
echo "Data directory: ./data"
echo "Open http://localhost:5000 in your browser"
echo ""

uvicorn app:app --host 0.0.0.0 --port 5000 --app-dir app "$@"
