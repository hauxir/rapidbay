[![Open Source Helpers](https://www.codetriage.com/hauxir/rapidbay/badges/users.svg)](https://www.codetriage.com/hauxir/rapidbay)
# RapidBay
Rapid bay is a self hosted video service/torrent client that makes playing videos from torrents as easy as:
1. Opening the webapp on a phone/laptop/tablet/smartTV.
2. Searching for content.
3. Selecting desired video file.
4. Waiting for Download/Conversion.
5. Playing on the device or cast to AppleTV/Chromecast

## Features:
- Search using a combination of the top torrent search engines - easily extendable to support other backends.
- Pick individual video files you want to play and the system takes care of the rest to make it streamable.
- Automatic download of Closed Captions/Subtitles
- Automatically converts the video file and subtitles to be playable on all browsers/chromecast/appletv
- Automatically converts audio that is unsupported by browsers to AAC
- Allows registering as a handler for any magnet link
- Automatically cleans up disk space so you don't need to manage it yourself
- Supports using [Jackett](https://github.com/Jackett/Jackett) as a search backend.

## Demo:
![](https://user-images.githubusercontent.com/2439255/48429861-44b60b00-e76e-11e8-8bdb-042f125357ce.gif)

## Running:
Requires Docker
```
docker run -p 5000:5000 -p 6881:6881 -p 6881:6881/udp -e USERNAME=<some-username> -e PASSWORD=<some-password> hauxir/rapidbay
```
App will be running at http://localhost:5000

## Configuring which subtitles to download:
The default setting downloads all subtitle languages but it might get slow if there are many for a given file.

To solve this you need to customize which languages you want.

Add the env variable SUBTITLE_LANGUAGES to your docker params like so:
```
-e SUBTITLE_LANGUAGES="['en', 'de', 'es']"
```
## Using Jackett as a search backend:
Rapidbay supports using the torrent indexer [Jackett](https://github.com/Jackett/Jackett) for searching.
Just provide the the env variables JACKETT_HOST and JACKETT_API_KEY like so:
```
-e JACKETT_HOST="http://your.jacket.host" -e JACKETT_API_KEY="YourAPIKey"
```

## Registering as a handler for any magnet link:
- Go to https://\<RAPIDBAY_HOST\>/registerHandler and it should prompt you to register your running RapidBay instance as a default handler for torrent links on any torrent site!
- You can also copy/paste a magnet link directly into the search bar to open magnet links manually.

## Developing
Requires Docker + docker-compose
```
docker-compose up
```
Default username and password is admin:123456

## Running RapidBay on a VPS

[Setting RapidBay up on a VPS and tunnel torrent traffic through NordVPN](https://github.com/hauxir/rapidbay/wiki/Setting-RapidBay-up-on-a-VPS-and-tunnel-torrent-traffic-through-NordVPN)
