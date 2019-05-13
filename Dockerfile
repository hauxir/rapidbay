FROM hauxir/libtorrent-python3-ubuntu:latest

RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    git \
    mediainfo

RUN pip install flask
RUN pip install lxml
RUN pip install aiohttp
RUN pip install beautifulsoup4
RUN pip install pymediainfo
RUN pip install Flask-BasicAuth
RUN pip install iso-639
RUN pip install -e git+https://github.com/agonzalezro/python-opensubtitles#egg=python-opensubtitles

# BitTorrent incoming
EXPOSE 6881
EXPOSE 6881/udp
EXPOSE 5000

COPY app /app

WORKDIR /app

CMD python app.py
