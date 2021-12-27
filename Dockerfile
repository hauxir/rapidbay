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
RUN pip install requests
RUN pip install -e git+https://github.com/agonzalezro/python-opensubtitles#egg=python-opensubtitles
RUN pip install bencodepy
RUN pip install parse-torrent-name
RUN pip install python-dateutil
RUN pip install gunicorn

# BitTorrent incoming
EXPOSE 6881
EXPOSE 6881/udp

# HTTP port
EXPOSE 5000

COPY app /app
COPY nginx.conf /etc/nginx/conf.d/default.conf

WORKDIR /app

CMD bash entrypoint.sh
