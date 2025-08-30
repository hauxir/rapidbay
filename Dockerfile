FROM hauxir/libtorrent-python3-ubuntu:latest

RUN apt-get update && \
    apt-get install -y \
    nginx \
    zip \
    ffmpeg \
    git \
    mediainfo

RUN wget https://github.com/kaegi/alass/releases/download/v2.0.0/alass-linux64 -O /usr/bin/alass
RUN chmod +x /usr/bin/alass

# BitTorrent incoming
EXPOSE 6881
EXPOSE 6881/udp

# HTTP port
EXPOSE 5000

COPY app /app
COPY mypy.ini /app/
COPY ruff.toml /app/
COPY nginx.conf /etc/nginx/conf.d/default.conf

WORKDIR /app

RUN pip install -r requirements.txt

CMD bash entrypoint.sh
