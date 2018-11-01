FROM hauxir/libtorrent-python3:latest

RUN apk update && \
    apk upgrade && \
    apk add ffmpeg && \
    apk add mediainfo

RUN pip install flask
RUN pip install requests
RUN pip install beautifulsoup4
RUN pip install pymediainfo
RUN pip install Flask-BasicAuth

# BitTorrent incoming
EXPOSE 6881
EXPOSE 6881/udp
EXPOSE 5000

COPY . /app

WORKDIR /app

CMD python app.py
