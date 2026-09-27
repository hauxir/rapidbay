"""Enrich flat torrent search results with TMDB metadata and buckets."""

import re
from datetime import date, timedelta
from typing import Any

from title_parser import parse_title
from tmdb import TMDBClient

MAX_TMDB_LOOKUPS: int = 30


def _clean_fallback_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    translated = value.translate(str.maketrans({".": " ", "-": " ", "_": " "}))
    return " ".join(translated.split())


def _normalized_title(value: str) -> str:
    return value.strip().casefold()


def _part_one_alias(normalized: str) -> str | None:
    """Map "Dune Part One" onto "Dune", the title TMDB uses for that film."""
    simplified = " ".join(re.sub(r"[:._-]+", " ", normalized).split())
    aliased = re.sub(r"\s+part\s+(?:one|1|i)$", "", simplified)
    if aliased and aliased != simplified:
        return aliased
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _year_from_details(details: dict[str, Any], media_type: str) -> int | None:
    year = _as_int(details.get("year"))
    if year is not None:
        return year

    date_key = "first_air_date" if media_type == "tv" else "release_date"
    date_value = details.get(date_key)
    if isinstance(date_value, str) and len(date_value) >= 4:
        return _as_int(date_value[:4])
    return None


def _details_for_match(
    client: TMDBClient, match: dict[str, Any]
) -> tuple[str, dict[str, Any]] | None:
    media_type = match.get("media_type")
    tmdb_id = _as_int(match.get("id"))
    if media_type not in ("tv", "movie") or tmdb_id is None:
        return None

    first_type, second_type = ("tv", "movie") if media_type == "tv" else ("movie", "tv")
    for candidate_type in (first_type, second_type):
        try:
            if candidate_type == "tv":
                details = client.get_tv_details(tmdb_id)
            else:
                details = client.get_movie_details(tmdb_id)
        except Exception:
            details = None
        if isinstance(details, dict) and details:
            return candidate_type, details
    return None


def _card_details(client: TMDBClient, details: dict[str, Any]) -> dict[str, Any]:
    """Plot, genres, rating, backdrop, and runtime already present on a details response."""
    overview = details.get("overview")
    overview_text = overview.strip() if isinstance(overview, str) else ""

    genres: list[str] = []
    raw_genres = details.get("genres")
    if isinstance(raw_genres, list):
        for genre in raw_genres:
            name = genre.get("name") if isinstance(genre, dict) else None
            if isinstance(name, str) and name.strip() and name.strip() not in genres:
                genres.append(name.strip())

    vote_average = None
    vote = details.get("vote_average")
    vote_count = details.get("vote_count")
    if isinstance(vote, (int, float)) and not isinstance(vote, bool) and vote_count != 0:
        vote_average = round(float(vote), 1)

    backdrop_url = None
    backdrop_path = details.get("backdrop_path")
    if isinstance(backdrop_path, str) and backdrop_path:
        try:
            backdrop_url = client.get_image_url(backdrop_path, size="w780")
        except Exception:
            backdrop_url = None

    runtime = _as_int(details.get("runtime"))
    if runtime is not None and runtime <= 0:
        runtime = None

    return {
        "overview": overview_text or None,
        "genres": genres,
        "vote_average": vote_average,
        "backdrop_url": backdrop_url,
        "runtime": runtime,
    }


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _rating(details: dict[str, Any]) -> float | None:
    vote = details.get("vote_average")
    if not isinstance(vote, (int, float)) or isinstance(vote, bool) or details.get("vote_count") == 0:
        return None
    return round(float(vote), 1)


def _aired_within_two_weeks(air_date: str | None) -> bool:
    """True when the episode aired today or within the previous 13 days."""
    if not air_date:
        return False
    try:
        released = date.fromisoformat(air_date)
    except ValueError:
        return False
    age = date.today() - released
    return timedelta(0) <= age < timedelta(days=14)


def _latest_episode(client: TMDBClient, details: dict[str, Any]) -> dict[str, Any] | None:
    """The latest aired episode, when it was released less than two weeks ago."""
    episode = details.get("last_episode_to_air")
    if not isinstance(episode, dict):
        return None
    season_number = _as_int(episode.get("season_number"))
    episode_number = _as_int(episode.get("episode_number"))
    air_date = _text(episode.get("air_date"))
    if season_number is None or episode_number is None or not _aired_within_two_weeks(air_date):
        return None

    runtime = _as_int(episode.get("runtime"))
    if runtime is not None and runtime <= 0:
        runtime = None

    still_url = None
    still_path = episode.get("still_path")
    if isinstance(still_path, str) and still_path:
        try:
            still_url = client.get_image_url(still_path, size="w300")
        except Exception:
            still_url = None

    return {
        "name": _text(episode.get("name")),
        "overview": _text(episode.get("overview")),
        "season_number": season_number,
        "episode_number": episode_number,
        "air_date": air_date,
        "runtime": runtime,
        "vote_average": _rating(episode),
        "still_url": still_url,
    }


def season_episode_details(client: TMDBClient, payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Episode cards for one season: name, plot, air date, runtime, rating, and still."""
    if not isinstance(payload, dict):
        return []
    raw_episodes = payload.get("episodes")
    if not isinstance(raw_episodes, list):
        return []

    episodes: list[dict[str, Any]] = []
    for episode in raw_episodes:
        if not isinstance(episode, dict):
            continue
        episode_number = _as_int(episode.get("episode_number"))
        if episode_number is None:
            continue
        runtime = _as_int(episode.get("runtime"))
        if runtime is not None and runtime <= 0:
            runtime = None
        still_url = None
        still_path = episode.get("still_path")
        if isinstance(still_path, str) and still_path:
            try:
                still_url = client.get_image_url(still_path, size="w300")
            except Exception:
                still_url = None
        episodes.append(
            {
                "episode_number": episode_number,
                "name": _text(episode.get("name")),
                "overview": _text(episode.get("overview")),
                "air_date": _text(episode.get("air_date")),
                "runtime": runtime,
                "vote_average": _rating(episode),
                "still_url": still_url,
            }
        )
    episodes.sort(key=lambda item: int(item["episode_number"]))
    return episodes


def _make_group(
    client: TMDBClient,
    match: dict[str, Any],
    query_title: str,
    media_type: str,
    details: dict[str, Any],
) -> tuple[tuple[str, int], dict[str, Any]] | None:
    tmdb_id = _as_int(match.get("id"))
    if tmdb_id is None:
        return None

    if media_type == "tv":
        display_title = details.get("name") or details.get("original_name")
        search_title = match.get("name") or match.get("original_name")
    else:
        display_title = details.get("title") or details.get("original_title")
        search_title = match.get("title") or match.get("original_title")
    title = display_title or search_title or query_title
    if not isinstance(title, str) or not title.strip():
        title = query_title

    poster_path = details.get("poster_path") or match.get("poster_path")
    try:
        poster_url = client.get_image_url(poster_path) if isinstance(poster_path, str) else None
    except Exception:
        poster_url = None

    year = _year_from_details(details, media_type)
    if year is None:
        year = _year_from_details(match, media_type)

    group: dict[str, Any] = {
        "tmdb_id": tmdb_id,
        "title": title,
        "year": year,
        "poster_url": poster_url,
        "media_type": media_type,
        "seasons": {} if media_type == "tv" else [],
        "results": [] if media_type == "movie" else [],
    }
    group.update(_card_details(client, details))
    group["adult"] = details.get("adult") is True or details.get("softcore") is True
    if media_type == "tv":
        latest = _latest_episode(client, details)
        if latest is not None:
            group["latest_episode"] = latest
    return (media_type, tmdb_id), group


def _parsed_seasons(parsed: dict[str, Any]) -> list[int]:
    """Seasons a torrent belongs to. A pack covering several seasons lists each one."""
    raw_seasons = parsed.get("seasons")
    if isinstance(raw_seasons, list):
        seasons: list[int] = []
        for item in raw_seasons:
            number = _as_int(item)
            if number is not None and number not in seasons:
                seasons.append(number)
        if seasons:
            return seasons
    season = _as_int(parsed.get("season"))
    return [season] if season is not None else []


def _add_result_to_group(group: dict[str, Any], result: dict[str, Any], parsed: dict[str, Any]) -> bool:
    if group["media_type"] == "movie":
        if _parsed_seasons(parsed):
            return False
        movie_results: list[dict[str, Any]] = group["results"]
        movie_results.append(dict(result))
        return True

    season_numbers = _parsed_seasons(parsed)
    if not season_numbers:
        return False
    seasons: dict[int, list[tuple[int | None, str, dict[str, Any]]]] = group["seasons"]
    episode = None if len(season_numbers) > 1 else _as_int(parsed.get("episode"))
    title = result.get("title")
    title_text = title if isinstance(title, str) else ""
    for season in season_numbers:
        seasons.setdefault(season, []).append((episode, title_text.casefold(), dict(result)))
    return True


def _candidate_year(candidate: dict[str, Any]) -> int | None:
    media_type = candidate.get("media_type")
    if media_type not in ("tv", "movie"):
        return None
    return _year_from_details(candidate, media_type)


def _select_group_for_result(
    groups: list[dict[str, Any]],
    parsed: dict[str, Any],
) -> dict[str, Any] | None:
    """Pick the card a torrent belongs on.

    Movie filenames that include a year only join the card for that year.
    Episodes stay on the TV card, because a filename year is often the air
    date rather than the series premiere. A release dated from before the
    show existed stays off that card.
    """
    if not groups:
        return None
    parsed_year = _as_int(parsed.get("year"))
    if _parsed_seasons(parsed):
        tv_groups = [group for group in groups if group["media_type"] == "tv"]
        for group in tv_groups:
            show_year = group.get("year")
            if parsed_year is not None and isinstance(show_year, int) and parsed_year < show_year - 1:
                continue
            return group
        return None
    if parsed_year is not None:
        for group in groups:
            if group["media_type"] == "movie" and group.get("year") == parsed_year:
                return group
        return None
    return groups[0]


def _group_result_count(group: dict[str, Any]) -> int:
    if group["media_type"] == "tv":
        seasons = group["seasons"]
        if isinstance(seasons, dict):
            return sum(len(episodes) for episodes in seasons.values())
        return sum(len(season.get("episodes") or []) for season in seasons)
    results = group.get("results")
    return len(results) if isinstance(results, list) else 0


def _group_has_results(group: dict[str, Any]) -> bool:
    if group["media_type"] == "tv":
        seasons = group["seasons"]
        return isinstance(seasons, dict) and any(seasons.values())
    results = group.get("results")
    return isinstance(results, list) and len(results) > 0


def _serialized_group(group: dict[str, Any]) -> dict[str, Any]:
    if group["media_type"] != "tv":
        return group

    seasons: dict[int, list[tuple[int | None, str, dict[str, Any]]]] = group["seasons"]
    group["seasons"] = [
        {
            "season": season,
            "episodes": [
                result
                for _, _, result in sorted(
                    episodes,
                    key=lambda item: (
                        item[0] is None,
                        item[0] if item[0] is not None else 0,
                        item[1],
                    ),
                )
            ],
        }
        for season, episodes in sorted(seasons.items())
    ]
    return group


def _accepted_titles(*names: Any) -> set[str]:
    accepted: set[str] = set()
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        normalized = _normalized_title(_clean_fallback_title(name))
        if not normalized:
            continue
        accepted.add(normalized)
        alias = _part_one_alias(normalized)
        if alias:
            accepted.add(alias)
    return accepted


def _title_is_accepted(parsed_title: str, accepted: set[str]) -> bool:
    normalized = _normalized_title(parsed_title)
    if not normalized:
        return False
    if normalized in accepted:
        return True
    alias = _part_one_alias(normalized)
    return alias is not None and alias in accepted


def _enrich_focused(
    parsed_results: list[tuple[dict[str, Any], dict[str, Any], str]],
    client: TMDBClient | None,
    media_type: str,
    tmdb_id: int,
    query_title: str,
) -> dict[str, Any]:
    """One known title. Other torrent matches are dropped and never sent to TMDB."""
    empty: dict[str, Any] = {"groups": [], "other": []}
    if client is None or media_type not in ("tv", "movie"):
        return empty
    try:
        details = client.get_tv_details(tmdb_id) if media_type == "tv" else client.get_movie_details(tmdb_id)
    except Exception:
        details = None
    if not isinstance(details, dict) or not details:
        return empty
    made = _make_group(
        client,
        {"id": tmdb_id, "media_type": media_type},
        query_title,
        media_type,
        details,
    )
    if made is None:
        return empty
    _, group = made
    accepted = _accepted_titles(group.get("title"), query_title)
    for result, parsed, parsed_title in parsed_results:
        if not _title_is_accepted(parsed_title, accepted):
            continue
        if media_type == "movie" and _parsed_seasons(parsed):
            continue
        selected = _select_group_for_result([group], parsed)
        if selected is None:
            continue
        _add_result_to_group(selected, result, parsed)
    return {"groups": [_serialized_group(group)], "other": []}


def enrich_search_results(
    results: list[dict[str, Any]],
    tmdb_api_key: str | None,
    focus: tuple[str, int] | None = None,
    query_title: str = "",
) -> dict[str, Any]:
    """Return TMDB groups and unmatched results from a flat torrent list.

    Searches are deduplicated by the parsed, cleaned title and capped at
    ``MAX_TMDB_LOOKUPS``. Movie releases join the card for the year in the
    filename. The returned season structure is JSON-serializable and follows
    the API shape ``[{"season": n, "episodes": [...]}]``.
    """
    parsed_results: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    unique_titles: dict[str, str] = {}
    for result in results:
        raw_title = result.get("title") if isinstance(result, dict) else None
        fallback_title = _clean_fallback_title(raw_title)
        try:
            parsed = parse_title(raw_title) if isinstance(raw_title, str) else {}
        except Exception:
            parsed = {}

        parsed_title = parsed.get("title")
        if not isinstance(parsed_title, str) or not parsed_title.strip():
            parsed_title = fallback_title
        parsed_title = _clean_fallback_title(parsed_title)
        if not parsed_title:
            parsed_title = str(raw_title).strip() if raw_title is not None else ""

        parsed_results.append((result, parsed, parsed_title))
        normalized = _normalized_title(parsed_title)
        if normalized:
            unique_titles.setdefault(normalized, parsed_title)

    if focus is not None:
        media_type, tmdb_id = focus
        client = TMDBClient(tmdb_api_key) if tmdb_api_key else None
        return _enrich_focused(parsed_results, client, media_type, tmdb_id, query_title)

    movie_years_by_title: dict[str, set[int]] = {}
    tv_titles: set[str] = set()
    for _, parsed, parsed_title in parsed_results:
        normalized_title = _normalized_title(parsed_title)
        if not normalized_title:
            continue
        if _parsed_seasons(parsed):
            tv_titles.add(normalized_title)
            continue
        parsed_year = _as_int(parsed.get("year"))
        if parsed_year is not None:
            movie_years_by_title.setdefault(normalized_title, set()).add(parsed_year)

    groups_by_tmdb: dict[tuple[str, int], dict[str, Any]] = {}
    matched_titles: dict[str, list[tuple[str, int]]] = {}
    other: list[dict[str, Any]] = []

    if tmdb_api_key:
        client = TMDBClient(tmdb_api_key)
        for index, (normalized, title) in enumerate(unique_titles.items()):
            if index >= MAX_TMDB_LOOKUPS:
                break
            try:
                search_response = client.search_multi(title)
            except Exception:
                search_response = None
            candidates = search_response.get("results") if isinstance(search_response, dict) else None
            if not isinstance(candidates, list):
                continue

            movie_years = movie_years_by_title.get(normalized, set())
            needs_tv = normalized in tv_titles
            keys: list[tuple[str, int]] = []
            covered_years: set[int] = set()
            have_tv = False
            detail_lookups = 0
            for candidate in candidates:
                if detail_lookups >= 8:
                    break
                if not isinstance(candidate, dict):
                    continue
                candidate_media_type = candidate.get("media_type")
                candidate_year = _candidate_year(candidate)
                want_default = not keys
                uncovered_years = movie_years - covered_years
                want_year = candidate_media_type == "movie" and bool(uncovered_years) and (
                    candidate_year is None or candidate_year in uncovered_years
                )
                want_tv = needs_tv and not have_tv and candidate_media_type == "tv"
                if not (want_default or want_year or want_tv):
                    continue
                detail_lookups += 1
                resolved = _details_for_match(client, candidate)
                if resolved is None:
                    continue
                media_type, details = resolved
                group_data = _make_group(client, candidate, title, media_type, details)
                if group_data is None:
                    continue
                key, group = group_data
                if key not in groups_by_tmdb:
                    groups_by_tmdb[key] = group
                if key not in keys:
                    keys.append(key)
                if group["media_type"] == "tv":
                    have_tv = True
                group_year = group.get("year")
                if group["media_type"] == "movie" and isinstance(group_year, int):
                    covered_years.add(group_year)
                if covered_years >= movie_years and (not needs_tv or have_tv):
                    break
            if keys:
                matched_titles[normalized] = keys

    for result, parsed, parsed_title in parsed_results:
        normalized = _normalized_title(parsed_title)
        keys = matched_titles.get(normalized)
        group = None
        if keys is not None:
            groups = [groups_by_tmdb[key] for key in keys if key in groups_by_tmdb]
            group = _select_group_for_result(groups, parsed)
        if group is None:
            alias = _part_one_alias(normalized)
            alias_keys = matched_titles.get(alias) if alias is not None else None
            if alias_keys is not None:
                alias_groups = [groups_by_tmdb[key] for key in alias_keys if key in groups_by_tmdb]
                group = _select_group_for_result(alias_groups, parsed)
        if group is None or not _add_result_to_group(group, result, parsed):
            unmatched = dict(result)
            unmatched["parsed_title"] = parsed_title
            other.append(unmatched)

    ordered_groups = sorted(
        groups_by_tmdb.values(),
        key=lambda group: (-_group_result_count(group), str(group["title"]).casefold()),
    )
    return {
        "groups": [
            _serialized_group(group) for group in ordered_groups if _group_has_results(group)
        ],
        "other": other,
    }
