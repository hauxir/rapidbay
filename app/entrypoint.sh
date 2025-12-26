#!/bin/bash
# Docker entrypoint - set paths for container environment
export DATA_DIR="/tmp"
export FRONTEND_DIR="/app/frontend"
export KODI_ADDON_DIR="/app/kodi.addon"

nginx
uvicorn app:app --uds rapidbay.sock --workers 1 --timeout-keep-alive 900
