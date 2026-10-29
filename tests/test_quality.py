import pytest

from app.quality import is_cam, is_fake_uhd, is_low_quality

GIB = 1024 * 1024 * 1024


@pytest.mark.parametrize("title", [
    "New.Movie.2026.HDCAM.x264",
    "New Movie (2026) 1080p TS x264",
    "New.Movie.2026.TELESYNC.720p",
    "New Movie 2026 DVDScr XviD",
    "New Movie 2026 CAM",
    "New.Movie.2026.HDTC.1080p",
])
def test_flags_cam_releases(title: str) -> None:
    assert is_cam(title)


@pytest.mark.parametrize("title", [
    "Cambridge lectures on physics",
    "Webcam basics",
    "TS Eliot poetry reading",
    "lecture01.ts",
    "Scrubs complete",
    "Show.S01E01.1080p.WEB-DL.x265",
])
def test_ordinary_titles_are_not_cam(title: str) -> None:
    assert not is_cam(title)


def test_fake_uhd_by_size() -> None:
    assert is_fake_uhd("Movie.2025.2160p.x265", 400 * 1024 * 1024)
    assert not is_fake_uhd("Movie.2025.2160p.x265", 14 * GIB)
    assert not is_fake_uhd("Movie.2025.2160p", None)
    assert not is_fake_uhd("Movie.2025.1080p", 300 * 1024 * 1024)


def test_hevc_is_not_low_quality() -> None:
    assert not is_low_quality({"title": "Movie.2025.2160p.HEVC.HDR", "size": 20 * GIB})
    assert is_low_quality({"title": "Movie.2025.4K", "size": 100 * 1024 * 1024})
    assert not is_low_quality({"title": "Movie.2025.4K", "size": "garbage"})
