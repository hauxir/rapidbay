FROM hauxir/libtorrent-python3-ubuntu:latest

RUN apt-get update && \
    apt-get install -y \
    nginx \
    zip \
    ffmpeg \
    git \
    mediainfo

RUN pip install flask
RUN pip install lxml
RUN pip install pymediainfo==4.2.1
RUN pip install iso-639
RUN pip install requests==2.31.0
RUN pip install -e git+https://github.com/agonzalezro/python-opensubtitles#egg=python-opensubtitles
RUN pip install bencodepy
RUN pip install parse-torrent-name
RUN pip install python-dateutil
RUN pip install gunicorn
RUN pip install requests_unixsocket
RUN pip install aiohttp
RUN pip install lockfile
RUN pip install diskcache
RUN pip install urllib3==1.26.16

# Install mypy type stubs for third-party libraries
RUN pip install mypy
RUN pip install types-flask
RUN pip install types-lxml
RUN pip install types-requests
RUN pip install types-python-dateutil
RUN pip install types-urllib3
RUN pip install types-setuptools
RUN pip install types-libtorrent

# Install ruff for linting
RUN pip install ruff

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

CMD bash entrypoint.sh
