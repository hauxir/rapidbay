# Build stage
FROM ubuntu:24.04 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    wget \
    ca-certificates \
    python3 \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Download alass binary
RUN wget https://github.com/kaegi/alass/releases/download/v2.0.0/alass-linux64 -O /usr/bin/alass && \
    chmod +x /usr/bin/alass

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock .python-version ./

# Install Python dependencies (without local package)
RUN uv sync --frozen --no-cache --no-dev --no-install-project

# Copy app code and install local package
COPY app ./app
RUN uv sync --frozen --no-cache --no-dev

# Runtime stage
FROM ubuntu:24.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    nginx \
    ffmpeg \
    mediainfo \
    ca-certificates \
    python3 \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy alass binary from builder
COPY --from=builder /usr/bin/alass /usr/bin/alass

# Copy virtual environment from builder
COPY --from=builder /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# BitTorrent incoming
EXPOSE 6881
EXPOSE 6881/udp

# HTTP port
EXPOSE 5000

COPY app /app
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN chmod +x /app/run.sh
WORKDIR /app

ENV USE_NGINX=1 DATA_DIR=/tmp FRONTEND_DIR=/app/frontend KODI_ADDON_DIR=/app/kodi.addon

CMD ["./run.sh"]
