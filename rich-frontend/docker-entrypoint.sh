#!/bin/sh
set -eu

# The .env copied into the image is the address a redeploy should use.
# An external RAPIDBAY_API_URL applies only when that file is absent.
if [ -f /etc/rapidbay/.env ]; then
    set -a
    # shellcheck disable=SC1091
    . /etc/rapidbay/.env
    set +a
fi

api_url="${RAPIDBAY_API_URL:-http://127.0.0.1:5000}"
api_url=$(printf '%s' "$api_url" | tr -d '\r' | sed 's:/*$::')
escaped=$(printf '%s' "$api_url" | sed 's/\\/\\\\/g; s/"/\\"/g')
printf 'window.RAPIDBAY_API_URL = "%s";\n' "$escaped" > /usr/share/nginx/html/config.js
