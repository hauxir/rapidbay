"""HLS streams carry every audio track as its own rendition."""

import os

from app.video_conversion import build_hls_command, write_hls_master_playlist


def _arg(cmd, flag):
    return cmd[cmd.index(flag) + 1]


def test_single_audio_keeps_muxed_media_playlist(tmp_path):
    cmd, playlists = build_hls_command(
        str(tmp_path), "ep.m3u8", "avc1", "ac-3", [{"codec": "ac3", "language": "eng", "default": True}]
    )
    assert "-var_stream_map" not in cmd and "-map" not in cmd
    assert playlists == [cmd[-1]] == [os.path.join(tmp_path, "ep.m3u8")]


def test_multi_audio_maps_every_track_as_a_rendition(tmp_path):
    streams = [
        {"codec": "aac", "language": "eng", "default": False},
        {"codec": "ac3", "language": "ice", "default": True},
        {"codec": "dts", "language": "bad lang,x", "default": False},
    ]
    cmd, playlists = build_hls_command(str(tmp_path), "ep.m3u8", "avc1", "aac", streams)

    assert [cmd[i + 1] for i, a in enumerate(cmd) if a == "-map"] == ["0:V:0", "0:a:0", "0:a:1", "0:a:2"]
    assert [_arg(cmd, f"-c:a:{i}") for i in range(3)] == ["copy", "aac", "aac"]
    # Source default is kept; a language that would break the map is dropped.
    assert _arg(cmd, "-var_stream_map") == (
        "v:0,agroup:aud,name:video "
        "a:0,agroup:aud,name:audio0,language:eng "
        "a:1,agroup:aud,name:audio1,language:ice,default:yes "
        "a:2,agroup:aud,name:audio2"
    )
    assert _arg(cmd, "-master_pl_name") == "ep.m3u8"
    assert playlists == [os.path.join(tmp_path, f"ep_{n}.m3u8") for n in ("video", "audio0", "audio1", "audio2")]


def test_master_merges_ffmpeg_renditions_with_subtitles(tmp_path):
    (tmp_path / "My Show.m3u8").write_text(
        "#EXTM3U\n#EXT-X-VERSION:7\n"
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="group_aud",NAME="audio_1",DEFAULT=YES,LANGUAGE="eng",URI="My Show_audio0.m3u8"\n'
        '#EXT-X-STREAM-INF:BANDWIDTH=281600,CODECS="avc1.64001f,mp4a.40.2",AUDIO="group_aud"\n'
        "My Show_video.m3u8\n"
    )
    name = write_hls_master_playlist(str(tmp_path), "My Show.m3u8", ["My Show_eng.vtt"])
    lines = (tmp_path / name).read_text().splitlines()

    assert '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="group_aud",NAME="audio_1",DEFAULT=YES,LANGUAGE="eng",URI="My%20Show_audio0.m3u8"' in lines
    assert lines[-2:] == [
        '#EXT-X-STREAM-INF:BANDWIDTH=281600,CODECS="avc1.64001f,mp4a.40.2",AUDIO="group_aud",SUBTITLES="subs"',
        "My%20Show_video.m3u8",
    ]


def test_master_wraps_single_audio_media_playlist_unchanged(tmp_path):
    (tmp_path / "ep.m3u8").write_text('#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-MAP:URI="ep_init.mp4"\n')
    name = write_hls_master_playlist(str(tmp_path), "ep.m3u8", [])
    assert (tmp_path / name).read_text() == "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=2000000\nep.m3u8\n"
