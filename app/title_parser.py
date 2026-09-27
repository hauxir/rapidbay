import datetime
import re
from typing import Any

import PTN

_SEASON_PATTERN = re.compile(r"[Ss](\d{1,2})")
_EPISODE_PATTERN = re.compile(r"[Ee](\d{1,2})")
_TITLE_SEPARATORS = re.compile(r"[.\-_]+")
_WHITESPACE = re.compile(r"\s+")
_PAREN_YEAR = re.compile(r"\(((?:19|20)\d{2})\)")
_YEAR_TOKEN = re.compile(r"(?:19|20)\d{2}")
_QUALITY_AFTER_YEAR = (
    r"(?:2160p|1080p|720p|576p|480p|bluray|blu-ray|webrip|web-dl|webdl|"
    r"hdrip|brrip|dvdrip|hdtv|hd-ts|remux)"
)
_SEASON_SUFFIX = re.compile(
    r"(?:\s+(?:s\d{1,2}(?:e\d{1,2})?|season\s+\d{1,2}|complete))+$",
    re.IGNORECASE,
)
_SEASON_WORD_RANGE = re.compile(
    r"\bseasons?\s+(\d{1,2})\s*(?:to|thru|through|[-–—~])\s*(?:season\s+)?(\d{1,2})\b",
    re.IGNORECASE,
)
_SEASON_CODE_RANGE = re.compile(
    r"(?<![A-Za-z0-9])S(\d{1,2})(?:[ ._-]*E\d{1,2})?\s*(?:to|thru|through|[-–—~])\s*"
    r"S(\d{1,2})(?:[ ._-]*E\d{1,2})?",
    re.IGNORECASE,
)
_SINGLE_SEASON_CODE = re.compile(
    r"(?<![A-Za-z0-9])S(\d{1,2})(?!\d)(?![ ._-]*E\d)",
    re.IGNORECASE,
)
_SEASON_WORD = re.compile(r"\bseason\s+(\d{1,2})\b", re.IGNORECASE)
_EPISODE_CODE = re.compile(
    r"(?<![A-Za-z0-9])S\d{1,2}[ ._-]*E\d{1,2}(?!\d)",
    re.IGNORECASE,
)
_EPISODE_WORD = re.compile(r"\bepisode\s+\d{1,2}\b", re.IGNORECASE)
_RELEASE_MARKERS = re.compile(
    r"(?:"
    r"\bseasons?\s+\d{1,2}\s*(?:to|thru|through|[-–—~])\s*(?:season\s+)?\d{1,2}\b"
    r"|"
    r"(?<![A-Za-z0-9])S\d{1,2}(?:[ ._-]*E\d{1,2})?\s*(?:to|thru|through|[-–—~])\s*"
    r"S\d{1,2}(?:[ ._-]*E\d{1,2})?"
    r"|"
    r"(?<![A-Za-z0-9])S\d{1,2}(?:[ ._-]*E\d{1,2})?(?![A-Za-z0-9])"
    r"|"
    r"\bseasons?\s+\d{1,2}\b"
    r"|"
    r"\bcomplete\b"
    r"|"
    r"\b(?:mp4|mkv|avi|m4v|wmv|mov|mpg|mpeg)\b"
    r")",
    re.IGNORECASE,
)
_MAX_SEASON_SPAN = 30


def _clean_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _WHITESPACE.sub(" ", _TITLE_SEPARATORS.sub(" ", value)).strip()


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _year_from_excess(value: Any) -> int | None:
    tokens = value if isinstance(value, list) else [value]
    for token in tokens:
        if not isinstance(token, str):
            continue
        match = _YEAR_TOKEN.fullmatch(token.strip("[]() "))
        if match:
            return int(match.group(0))
    return None


def _release_year(parsed: dict[str, Any], title: str) -> int | None:
    """Return the release year, including years PTN leaves out of its year field.

    Bracketed names such as ``Dune (2021) [1080p]`` often put 2020s years in
    ``excess`` instead of ``year``.
    """
    year = _as_int(parsed.get("year"))
    if year is not None and 1900 <= year <= 2099:
        return year
    parenthetical = _PAREN_YEAR.search(title)
    if parenthetical:
        return int(parenthetical.group(1))
    return _year_from_excess(parsed.get("excess"))


def _year_precedes_quality(raw_title: str, year: int) -> bool:
    return (
        re.search(
            rf"(?:^|[^0-9]){year}(?![0-9]).{{0,80}}?{_QUALITY_AFTER_YEAR}",
            raw_title,
            re.IGNORECASE,
        )
        is not None
    )


def _split_release_year(cleaned_title: str, raw_title: str) -> tuple[str, int | None]:
    """Pull a release year PTN left attached to the title.

    Dotted names such as ``Dune.2021.1080p`` and tagged names such as
    ``Dune Part Two 2024 NORDiC`` become the movie title plus a year.
    A year after next year is left alone so Blade Runner 2049 stays intact.
    """
    latest_year = datetime.date.today().year + 1
    for match in reversed(list(_YEAR_TOKEN.finditer(cleaned_title))):
        year = int(match.group(0))
        if year > latest_year or not _year_precedes_quality(raw_title, year):
            continue
        body = cleaned_title[: match.start()].strip(" ._-")
        if not body:
            continue
        return body, year
    return cleaned_title, None


def _has_season_token(value: str) -> bool:
    return bool(
        _SINGLE_SEASON_CODE.search(value)
        or _SEASON_WORD.search(value)
        or _SEASON_WORD_RANGE.search(value)
        or _SEASON_CODE_RANGE.search(value)
        or _EPISODE_CODE.search(value)
    )


def _keep_stripped(original: str, stripped: str) -> str:
    """Use the stripped name, including a one-word show, when a season was removed.

    ``MobLand S02`` becomes ``MobLand``. ``Mission Complete`` stays as it is,
    because nothing in it identifies a season.
    """
    if not stripped:
        return original
    if len(stripped.split()) >= 2 or _has_season_token(original):
        return stripped
    return original


def _strip_season_suffix(cleaned_title: str) -> str:
    """Drop a trailing ``S01`` or ``COMPLETE`` when a show name remains."""
    stripped = _SEASON_SUFFIX.sub("", cleaned_title).strip()
    return _keep_stripped(cleaned_title, stripped)


def _season_span(start: int, end: int) -> list[int] | None:
    if start > end:
        start, end = end, start
    if end - start > _MAX_SEASON_SPAN:
        return None
    return list(range(start, end + 1))


def _season_pack(raw_title: str) -> list[int] | None:
    """Seasons covered by a pack, or None when the name is a single episode.

    ``S04`` and ``Season 4`` are one season. ``Seasons 1 to 5`` and ``S01-S05``
    cover every season in the range. A lone ``S04E01`` is an episode.
    """
    word_range = _SEASON_WORD_RANGE.search(raw_title)
    if word_range:
        return _season_span(int(word_range.group(1)), int(word_range.group(2)))
    code_range = _SEASON_CODE_RANGE.search(raw_title)
    if code_range:
        return _season_span(int(code_range.group(1)), int(code_range.group(2)))
    if _EPISODE_CODE.search(raw_title) or _EPISODE_WORD.search(raw_title):
        return None

    seasons: list[int] = []
    for pattern in (_SINGLE_SEASON_CODE, _SEASON_WORD):
        for match in pattern.finditer(raw_title):
            number = int(match.group(1))
            if number not in seasons:
                seasons.append(number)
    return seasons or None


def _strip_release_markers(cleaned_title: str) -> str:
    """Drop season tokens and leftover container names from a show title."""
    stripped = _WHITESPACE.sub(" ", _RELEASE_MARKERS.sub(" ", cleaned_title)).strip(" ._-")
    return _keep_stripped(cleaned_title, stripped)


def parse_title(title: str) -> dict[str, Any]:
    if not title or not title.strip():
        raise ValueError("title must not be empty")

    try:
        parsed = PTN.parse(title)
    except Exception:
        return {}

    parsed_title = _clean_title(parsed.get("title"))
    cleaned_title = parsed_title or _clean_title(title)
    year = _release_year(parsed, title)
    if year is None:
        cleaned_title, year = _split_release_year(cleaned_title, title)
    cleaned_title = _strip_release_markers(_strip_season_suffix(cleaned_title))

    season = _as_int(parsed.get("season"))
    if season is None:
        season_match = _SEASON_PATTERN.search(title)
        if season_match:
            season = int(season_match.group(1))

    episode = _as_int(parsed.get("episode"))
    if episode is None:
        episode_match = _EPISODE_PATTERN.search(title)
        if episode_match:
            episode = int(episode_match.group(1))

    pack = _season_pack(title)
    if pack:
        episode = None
        season = pack[0] if len(pack) == 1 else None

    parsed_result: dict[str, Any] = {
        "title": cleaned_title,
        "season": season,
        "episode": episode,
        "year": year,
    }
    if pack and len(pack) > 1:
        parsed_result["seasons"] = pack
    return parsed_result
