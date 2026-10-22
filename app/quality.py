import re
from typing import Any, Dict, List

# Release-title heuristics for demoting results that are rarely what anyone
# wants to watch. Titles are split into whole lowercase words so "Cambridge"
# isn't a cam recording and "TS Eliot" isn't a telesync.

# Words that only ever mean a camera/telesync/telecine/screener release.
_CAM_WORDS = frozenset({
    "camrip", "hdcam", "hqcam", "telesync", "hdts", "hdtc", "telecine",
    "screener", "dvdscr", "bdscr", "webscreener", "predvd",
})
# Short tags that are also ordinary words or file extensions; they only count
# in titles that otherwise look like a video release.
_AMBIGUOUS_CAM_WORDS = frozenset({"cam", "tc", "scr", "ts"})
_UHD_WORDS = frozenset({"2160p", "4k", "uhd", "3840x2160", "4096x2160"})
_RELEASE_WORDS = frozenset({
    "2160p", "1080p", "1080i", "720p", "480p", "576p", "x264", "x265", "h264",
    "h265", "hevc", "avc", "av1", "xvid", "divx",
})
_YEAR = re.compile(r"^(19|20)\d\d$")

# Real 2160p video runs at 15-80 Mbit/s, so even a short film is several GB; a
# "4K" release under this size is mislabeled or upscaled junk.
MIN_UHD_BYTES = 600 * 1024 * 1024


def _words(title: str) -> List[str]:
    return [w for w in re.split(r"[^0-9a-z]+", title.lower()) if w]


def _looks_like_release(words: List[str]) -> bool:
    return any(w in _RELEASE_WORDS or _YEAR.match(w) for w in words)


def is_cam(title: str) -> bool:
    words = _words(title)
    if any(w in _CAM_WORDS for w in words):
        return True
    if not _looks_like_release(words):
        return False
    # A trailing "ts" is a file extension, not a telesync tag.
    return any(
        w in _AMBIGUOUS_CAM_WORDS and not (w == "ts" and i == len(words) - 1)
        for i, w in enumerate(words)
    )


def is_fake_uhd(title: str, size: int | None) -> bool:
    if not size:
        return False
    return any(w in _UHD_WORDS for w in _words(title)) and size < MIN_UHD_BYTES


def is_low_quality(result: Dict[str, Any]) -> bool:
    title = result.get("title") or ""
    size = result.get("size")
    return is_cam(title) or is_fake_uhd(title, size if isinstance(size, int) else None)
