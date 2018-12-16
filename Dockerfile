FROM hauxir/libtorrent-python3:latest

RUN apk update && \
    apk upgrade && \
    apk add ffmpeg && \
    apk add git && \
    apk add mediainfo

RUN pip install flask
RUN pip install requests
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
