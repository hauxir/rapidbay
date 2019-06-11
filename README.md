# RapidBay
Rapid bay is a self hosted video service/torrent client that makes playing videos from torrents as easy as:
1. Opening the webapp on a phone/laptop/tablet.
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

## Demo:
![](https://user-images.githubusercontent.com/2439255/48429861-44b60b00-e76e-11e8-8bdb-042f125357ce.gif)

## Running:
Requires Docker
```
docker run -p 5000:5000 -p 6881:6881 -p 6881:6881/udp -e USERNAME=<some-username> -e PASSWORD=<some-password> hauxir/rapidbay
```
App will be running at http://localhost:5000

## Developing
Requires Docker + docker-compose
```
docker-compose up
```

## Running RapidBay on a VPS

[Setting RapidBay up on a VPS and tunnel torrent traffic through NordVPN](https://github.com/hauxir/rapidbay/wiki/Setting-RapidBay-up-on-a-VPS-and-tunnel-torrent-traffic-through-NordVPN)
