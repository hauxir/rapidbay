"""Tests for HLS audio renditions: a source with several audio tracks streams
each as its own EXT-X-MEDIA:TYPE=AUDIO rendition instead of ffmpeg's single
default pick."""

import os

from app import settings
from app.video_conversion import (
    _var_stream_language,
    build_hls_command,
    write_hls_master_playlist,
)


def _arg(cmd, flag):
    return cmd[cmd.index(flag) + 1]


def test_single_audio_keeps_muxed_media_playlist(tmp_path):
    cmd, playlists = build_hls_command(
        str(tmp_path), "ep.m3u8", "avc1", "ac-3", [{"codec": "ac3", "language": "eng", "default": True}]
    )
    assert "-var_stream_map" not in cmd and "-map" not in cmd
    assert _arg(cmd, "-acodec") == "aac"
    assert cmd[-1] == os.path.join(tmp_path, "ep.m3u8")
    assert playlists == [os.path.join(tmp_path, "ep.m3u8")]


def test_single_audio_copies_aac_and_tolerates_failed_probe(tmp_path):
    cmd, _ = build_hls_command(str(tmp_path), "ep.m3u8", "hvc1", "aac lc", None)
    assert _arg(cmd, "-c:a") == "copy"
    assert _arg(cmd, "-tag:v") == "hvc1"


def test_multi_audio_maps_every_track_as_a_rendition(tmp_path):
    streams = [
        {"codec": "aac", "language": "eng", "default": False},
        {"codec": "ac3", "language": "ice", "default": True},
        {"codec": "dts", "language": "bad lang,x", "default": False},
    ]
    cmd, playlists = build_hls_command(str(tmp_path), "ep.m3u8", "avc1", "aac", streams)

    maps = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-map"]
    assert maps == ["0:V:0", "0:a:0", "0:a:1", "0:a:2"]
    # AAC is copied; anything else is transcoded per stream.
    assert _arg(cmd, "-c:a:0") == "copy"
    assert _arg(cmd, "-c:a:1") == "aac" and _arg(cmd, "-b:a:1") == settings.AAC_BITRATE
    assert _arg(cmd, "-c:a:2") == "aac"
    assert _arg(cmd, "-var_stream_map") == (
        "v:0,agroup:aud,name:video "
        "a:0,agroup:aud,name:audio0,language:eng "
        "a:1,agroup:aud,name:audio1,language:ice,default:yes "
        "a:2,agroup:aud,name:audio2"
    )
    # ffmpeg's master lands where the daemon looks for the stream.
    assert _arg(cmd, "-master_pl_name") == "ep.m3u8"
    assert playlists == [
        os.path.join(tmp_path, f"ep_{n}.m3u8") for n in ("video", "audio0", "audio1", "audio2")
    ]


def test_multi_audio_defaults_to_first_track_without_disposition(tmp_path):
    streams = [{"codec": "aac", "language": "", "default": False}] * 2
    cmd, _ = build_hls_command(str(tmp_path), "ep.m3u8", "avc1", "aac", streams)
    assert _arg(cmd, "-var_stream_map").split(" ")[1].endswith(",default:yes")
    assert "default:yes" not in _arg(cmd, "-var_stream_map").split(" ")[2]


def test_var_stream_language_rejects_map_separators():
    assert _var_stream_language("eng") == "eng"
    assert _var_stream_language("pt-BR") == "pt-BR"
    assert _var_stream_language("und") == ""
    assert _var_stream_language("en g") == ""
    assert _var_stream_language("en,default:yes") == ""


FFMPEG_MASTER = (
    "#EXTM3U\n"
    "#EXT-X-VERSION:7\n"
    '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="group_aud",NAME="audio_1",DEFAULT=NO,LANGUAGE="eng",URI="My Show_audio0.m3u8"\n'
    '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="group_aud",NAME="audio_2",DEFAULT=YES,LANGUAGE="ice",URI="My Show_audio1.m3u8"\n'
    '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="group_aud",NAME="audio_3",DEFAULT=NO,LANGUAGE="eng",URI="My Show_audio2.m3u8"\n'
    '#EXT-X-STREAM-INF:BANDWIDTH=281600,RESOLUTION=320x240,CODECS="avc1.64001f,mp4a.40.2",AUDIO="group_aud"\n'
    "My Show_video.m3u8\n"
)


def test_master_merges_ffmpeg_audio_renditions_with_subtitles(tmp_path):
    (tmp_path / "My Show.m3u8").write_text(FFMPEG_MASTER)
    (tmp_path / "My Show_eng.vtt").write_text("WEBVTT\n")
    name = write_hls_master_playlist(str(tmp_path), "My Show.m3u8", ["My Show_eng.vtt"])
    lines = (tmp_path / name).read_text().splitlines()

    audio = [line for line in lines if "TYPE=AUDIO" in line]
    assert audio == [
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English 1",LANGUAGE="en",DEFAULT=NO,AUTOSELECT=YES,URI="My%20Show_audio0.m3u8"',
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Icelandic",LANGUAGE="is",DEFAULT=YES,AUTOSELECT=YES,URI="My%20Show_audio1.m3u8"',
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English 2",LANGUAGE="en",DEFAULT=NO,AUTOSELECT=YES,URI="My%20Show_audio2.m3u8"',
    ]
    assert lines[-2] == (
        '#EXT-X-STREAM-INF:BANDWIDTH=281600,RESOLUTION=320x240,'
        'CODECS="avc1.64001f,mp4a.40.2",AUDIO="audio",SUBTITLES="subs"'
    )
    # The variant is the video media playlist, never ffmpeg's master.
    assert lines[-1] == "My%20Show_video.m3u8"


def test_master_wraps_single_audio_media_playlist_unchanged(tmp_path):
    (tmp_path / "ep.m3u8").write_text("#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-MAP:URI=\"ep_init.mp4\"\n")
    name = write_hls_master_playlist(str(tmp_path), "ep.m3u8", [])
    assert (tmp_path / name).read_text() == "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=2000000\nep.m3u8\n"
