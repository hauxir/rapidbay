# RapidBay

Rapid bay is a self hosted video service/torrent client that makes playing videos from torrents as easy as:

1. Opening the webapp on a phone/laptop/tablet/smartTV.
2. Searching for content.
3. Selecting desired video file.
4. Waiting for Download/Conversion.
5. Playing on the device or cast to AppleTV/Chromecast

## Features:

-   Uses [Jackett](https://github.com/Jackett/Jackett) as a search backend.
-   Pick individual video files you want to play and the system takes care of the rest to make it streamable.
-   Automatic download of Closed Captions/Subtitles
-   Automatically converts the video file and subtitles to be playable on all browsers/chromecast/appletv
-   Automatically converts audio that is unsupported by browsers to AAC
-   Allows registering as a handler for any magnet link
-   Automatically cleans up disk space so you don't need to manage it yourself
-   Kodi support

## Demo:

![](https://user-images.githubusercontent.com/2439255/48429861-44b60b00-e76e-11e8-8bdb-042f125357ce.gif)

## Setting up Jackett as a search backend:

Rapidbay requires the torrent indexer [Jackett](https://github.com/Jackett/Jackett) for searching.
Have a look [here](https://github.com/Jackett/Jackett#installation-using-docker) on how to set it up using Docker.

There's also a [docker-compose example](https://github.com/hauxir/rapidbay/blob/master/docker-compose.example.with.jackett.yml) file to show how you can connect rapidbay and jackett together.

## Running:

### With Docker (recommended)

```
docker run -p 5000:5000 -e JACKETT_HOST="http://your.jacket.host" -e JACKETT_API_KEY="YourAPIKey" hauxir/rapidbay
```

### Without Docker

**System dependencies:**

```bash
# Ubuntu/Debian
sudo apt install python3 python3-venv ffmpeg mediainfo nginx

# macOS
brew install python ffmpeg mediainfo nginx
```

**Optional:** Install [alass](https://github.com/kaegi/alass/releases) for subtitle synchronization.

**Install Python dependencies:**

```bash
# Using uv (recommended)
uv sync

# Or using pip
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

**Run the app:**

```bash
# Set environment variables
export JACKETT_HOST="http://your.jacket.host"
export JACKETT_API_KEY="YourAPIKey"

# Run directly (without nginx)
cd app
uvicorn app:app --host 0.0.0.0 --port 5000 --workers 1 --timeout-keep-alive 900
```

App will be running at http://localhost:5000

## Subtitles

You'll need a VIP account at OpenSubtitles.org for it to work:
```
-e OPENSUBTITLES_USERNAME=someusername -e OPENSUBTITLES_PASSWORD=yourpassword
```
### Configuring which subtitles to download:

The default setting downloads english subtitles.

Add the env variable SUBTITLE_LANGUAGES to your docker params like so to get more languages:

```
-e SUBTITLE_LANGUAGES="['en', 'de', 'es']"
```

## Require a password:

Add the env variable PASSWORD to your docker params like so to prompt for a password when opening rapidbay:

```
-e PASSWORD=YOURPASSWORD
```

## Registering as a handler for any magnet link:

-   Go to https://\<RAPIDBAY_HOST\>/registerHandler and it should prompt you to register your running RapidBay instance as a default handler for torrent links on any torrent site!
-   You can also copy/paste a magnet link directly into the search bar to open magnet links manually.

## Developing

Requires Docker + docker-compose

```
docker-compose up
```

## Running RapidBay on a VPS

[Setting RapidBay up on a VPS and tunnel torrent traffic through NordVPN](https://github.com/hauxir/rapidbay/wiki/Setting-RapidBay-up-on-a-VPS-and-tunnel-torrent-traffic-through-NordVPN)

## Using Kodi as a frontend

[Setting up Rapidbay with Kodi](https://github.com/hauxir/rapidbay/wiki/Setting-up-Rapidbay-with-Kodi)

## Using Real Debrid caching

-   You can speed up downloads by using the torrent cache at real debrid
-   To do that set the env variable RD_TOKEN to the one on https://real-debrid.com/apitoken
