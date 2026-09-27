"""Resolve download and watch events to TMDB ids without blocking the request."""

import json
import os
import queue
import threading
import time
from datetime import date
from typing import Any

import settings
import stats
from result_grouping import (
    _card_details,
    _details_for_match,
    _parsed_seasons,
    _year_from_details,
    enrich_search_results,
)
from title_parser import parse_title
from tmdb import TMDBClient

_queue: queue.Queue[dict[str, Any]] = queue.Queue()
_start_lock = threading.Lock()
_started = False


def _empty() -> dict[str, Any]:
    return {"identities": {}, "titles": {}}


def _store_path() -> str:
    path = settings.LIBRARY_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return path


def _load() -> dict[str, Any]:
    try:
        with open(_store_path(), encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    data.setdefault("identities", {})
    data.setdefault("titles", {})
    return data


def _save(data: dict[str, Any]) -> None:
    path = _store_path()
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    os.replace(temporary, path)


def _safe_parse(title: str) -> dict[str, Any]:
    if not title.strip():
        return {}
    try:
        parsed = parse_title(title)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _magnet_hash(magnet: str | None) -> str:
    if not isinstance(magnet, str) or "btih:" not in magnet.lower():
        return ""
    start = magnet.lower().find("btih:") + 5
    end = magnet.find("&", start)
    raw = magnet[start:] if end == -1 else magnet[start:end]
    return raw.lower()


def _identity_key(parsed: dict[str, Any]) -> str:
    title = parsed.get("title")
    name = title.strip().casefold() if isinstance(title, str) else ""
    year = parsed.get("year") or ""
    kind = "tv" if _parsed_seasons(parsed) else "movie"
    return f"{kind}:{name}:{year}"


def _choose_parse(event: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Return the raw name, the parse used to identify it, and the parse used for the episode."""
    filename = event.get("filename") if isinstance(event.get("filename"), str) else ""
    title = event.get("title") if isinstance(event.get("title"), str) else ""
    from_file = _safe_parse(filename)
    from_title = _safe_parse(title)
    if from_file.get("title"):
        raw, identity = filename, from_file
    else:
        raw, identity = title, from_title
    episode = from_file if _parsed_seasons(from_file) else identity
    return raw, identity, episode


def _identity_from_group(group: dict[str, Any], raw_title: str) -> dict[str, Any] | None:
    media_type = group.get("media_type")
    tmdb_id = group.get("tmdb_id")
    if media_type not in ("tv", "movie") or not isinstance(tmdb_id, int):
        return None
    return {
        "tmdb_id": tmdb_id,
        "media_type": media_type,
        "title": group.get("title") or raw_title,
        "year": group.get("year"),
        "poster_url": group.get("poster_url"),
        "backdrop_url": group.get("backdrop_url"),
        "adult": group.get("adult") is True,
    }


def _resolve_identity_direct(raw_title: str) -> dict[str, Any] | None:
    """Look up a plain title when torrent grouping has nothing to attach it to."""
    parsed = _safe_parse(raw_title)
    query = parsed.get("title") if isinstance(parsed.get("title"), str) else ""
    query = query.strip() or raw_title.strip()
    if not query or not settings.TMDB_API_KEY:
        return None
    client = TMDBClient(settings.TMDB_API_KEY)
    try:
        response = client.search_multi(query)
    except Exception:
        return None
    candidates = response.get("results") if isinstance(response, dict) else None
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if not isinstance(candidate, dict) or candidate.get("media_type") not in ("tv", "movie"):
            continue
        resolved = _details_for_match(client, candidate)
        if resolved is None:
            continue
        media_type, details = resolved
        tmdb_id = details.get("id") if isinstance(details.get("id"), int) else candidate.get("id")
        if not isinstance(tmdb_id, int):
            continue
        title = details.get("name") if media_type == "tv" else details.get("title")
        poster_url = None
        poster_path = details.get("poster_path")
        if isinstance(poster_path, str) and poster_path:
            try:
                poster_url = client.get_image_url(poster_path, size="w185")
            except Exception:
                poster_url = None
        card = _card_details(client, details)
        return {
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "title": title if isinstance(title, str) and title.strip() else query,
            "year": _year_from_details(details, media_type),
            "poster_url": poster_url,
            "backdrop_url": card.get("backdrop_url"),
            "adult": details.get("adult") is True or details.get("softcore") is True,
        }
    return None


def _resolve_identity(raw_title: str) -> dict[str, Any] | None:
    if not raw_title.strip() or not settings.TMDB_API_KEY:
        return None
    try:
        enriched = enrich_search_results(
            [{"title": raw_title, "seeds": 0, "magnet": None}],
            settings.TMDB_API_KEY,
        )
    except Exception:
        enriched = None
    groups = enriched.get("groups") if isinstance(enriched, dict) else None
    if isinstance(groups, list) and groups:
        identity = _identity_from_group(groups[0], raw_title)
        if identity is not None:
            return identity
    return _resolve_identity_direct(raw_title)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _touch_download(item: dict[str, Any], magnet_hash: str, label: str, when: int) -> None:
    if not magnet_hash:
        return
    downloads: list[dict[str, Any]] = item.setdefault("downloads", [])
    for existing in downloads:
        if existing.get("hash") == magnet_hash:
            if when >= int(existing.get("at") or 0):
                existing["at"] = when
                existing["label"] = label
            return
    downloads.append({"hash": magnet_hash, "label": label, "at": when})
    downloads.sort(key=lambda entry: int(entry.get("at") or 0), reverse=True)
    del downloads[50:]


def _touch_episode(item: dict[str, Any], season: int, episode: int, filename: str, when: int) -> None:
    episodes: list[dict[str, Any]] = item.setdefault("watched_episodes", [])
    for existing in episodes:
        if existing.get("season") == season and existing.get("episode") == episode:
            if when >= int(existing.get("at") or 0):
                existing["at"] = when
                existing["filename"] = filename
            return
    episodes.append({"season": season, "episode": episode, "filename": filename, "at": when})
    episodes.sort(key=lambda entry: (entry["season"], entry["episode"]))


def process_event(event: dict[str, Any]) -> None:
    """Resolve one download or watch event and merge it into the library."""
    raw_title, identity_parsed, episode_parsed = _choose_parse(event)
    if not identity_parsed.get("title"):
        return
    key = _identity_key(identity_parsed)
    data = _load()
    identities: dict[str, Any] = data["identities"]
    cached = identities.get(key)
    if isinstance(cached, dict) and cached.get("unmatched"):
        return
    if not isinstance(cached, dict) or not cached.get("tmdb_id"):
        resolved = _resolve_identity(raw_title)
        if resolved is None:
            if settings.TMDB_API_KEY:
                identities[key] = {"unmatched": True}
                _save(data)
            return
        cached = resolved
        identities[key] = resolved

    when = _as_int(event.get("ts")) or 0
    kind = event.get("event")
    if kind == "search":
        _save(data)
        _record_activity(kind, cached, event, when, episode_parsed)
        return

    catalog_key = f"{cached['media_type']}:{cached['tmdb_id']}"
    titles: dict[str, Any] = data["titles"]
    item = titles.get(catalog_key)
    if not isinstance(item, dict):
        item = {
            "tmdb_id": cached["tmdb_id"],
            "media_type": cached["media_type"],
            "title": cached["title"],
            "year": cached.get("year"),
            "poster_url": cached.get("poster_url"),
            "backdrop_url": cached.get("backdrop_url"),
            "updated_at": 0,
            "watched_at": None,
            "watched_episodes": [],
            "downloads": [],
        }
        titles[catalog_key] = item

    label = event.get("filename") or event.get("title") or item["title"]
    label_text = label if isinstance(label, str) else item["title"]
    if cached.get("backdrop_url") and not item.get("backdrop_url"):
        item["backdrop_url"] = cached.get("backdrop_url")
    if kind == "progress":
        _touch_progress(item, event, episode_parsed, label_text, when)
        _save(data)
        return
    if kind == "download":
        _touch_download(item, _magnet_hash(event.get("magnet")), label_text, when)
    elif kind == "watched":
        if item["media_type"] == "movie":
            item["watched_at"] = max(int(item.get("watched_at") or 0), when)
        else:
            seasons = _parsed_seasons(episode_parsed)
            episode_number = _as_int(episode_parsed.get("episode"))
            if len(seasons) == 1 and episode_number is not None:
                _touch_episode(item, seasons[0], episode_number, label_text, when)
        _drop_progress(item, episode_parsed, label_text)
    if when >= int(item.get("updated_at") or 0):
        item["updated_at"] = when
    _save(data)
    _record_activity(kind, cached, event, when, episode_parsed)


def _record_activity(
    kind: str,
    identity: dict[str, Any],
    event: dict[str, Any],
    when: int,
    episode_parsed: dict[str, Any],
) -> None:
    try:
        if kind == "search":
            query = event.get("title") if isinstance(event.get("title"), str) else ""
            dedupe = stats.search_dedupe_key(identity, query, when)
        elif kind == "download":
            dedupe = f"download:{identity.get('media_type')}:{identity.get('tmdb_id')}:{_magnet_hash(event.get('magnet'))}"
        elif kind == "watched" and identity.get("media_type") == "movie":
            dedupe = f"watched:{identity.get('media_type')}:{identity.get('tmdb_id')}"
        elif kind == "watched":
            seasons = _parsed_seasons(episode_parsed)
            episode_number = _as_int(episode_parsed.get("episode"))
            if len(seasons) != 1 or episode_number is None:
                return
            dedupe = f"watched:{identity.get('media_type')}:{identity.get('tmdb_id')}:{seasons[0]}:{episode_number}"
        else:
            return
        stats.record(kind, identity, when, dedupe)
    except Exception:
        return


def _as_float(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _counts_as_finished(position: float, duration: float) -> bool:
    """Same finish line as the player: 98% watched, or under two minutes left."""
    if duration <= 0 or position <= 0:
        return False
    if position / duration >= 0.98:
        return True
    return duration >= 120 and duration - position < 120


def _minutes_left(position: float, duration: float) -> int | None:
    if duration <= 0 or position <= 0 or position >= duration:
        return None
    minutes = int(round((duration - position) / 60))
    return minutes if minutes > 0 else 1


def _finished_at(item: dict[str, Any], entry: dict[str, Any]) -> int | None:
    """When this movie or episode was finished, if it has been."""
    if item.get("media_type") == "movie":
        return _as_int(item.get("watched_at"))
    season = _as_int(entry.get("season"))
    episode = _as_int(entry.get("episode"))
    if season is None or episode is None:
        return None
    latest = None
    for watched in item.get("watched_episodes") or []:
        if not isinstance(watched, dict):
            continue
        if _as_int(watched.get("season")) != season or _as_int(watched.get("episode")) != episode:
            continue
        at = _as_int(watched.get("at")) or 0
        if latest is None or at > latest:
            latest = at
    return latest


def _progress_superseded(item: dict[str, Any], entry: dict[str, Any]) -> bool:
    """A finish replaces an earlier unfinished play. A later unfinished rewatch stays."""
    finished = _finished_at(item, entry)
    if finished is None:
        return False
    progress_at = _as_int(entry.get("at")) or 0
    if finished >= progress_at:
        return True
    # No file length means this is a leftover position, not a new viewing after the finish.
    return _as_float(entry.get("duration")) <= 0


def _progress_matches(entry: dict[str, Any], episode_parsed: dict[str, Any], filename: str, media_type: str) -> bool:
    if media_type == "movie":
        return True
    seasons = _parsed_seasons(episode_parsed)
    episode_number = _as_int(episode_parsed.get("episode"))
    if len(seasons) == 1 and episode_number is not None:
        if entry.get("season") == seasons[0] and entry.get("episode") == episode_number:
            return True
    return bool(filename) and entry.get("filename") == filename


def _drop_progress(item: dict[str, Any], episode_parsed: dict[str, Any], filename: str) -> None:
    progress = item.get("progress")
    if not isinstance(progress, list):
        return
    media_type = item.get("media_type")
    item["progress"] = [
        entry for entry in progress
        if not (isinstance(entry, dict) and _progress_matches(entry, episode_parsed, filename, str(media_type or "")))
    ]


def _touch_progress(
    item: dict[str, Any],
    event: dict[str, Any],
    episode_parsed: dict[str, Any],
    filename: str,
    when: int,
) -> None:
    """Remember a play that has passed two minutes and has not been finished."""
    position = _as_float(event.get("position"))
    duration = _as_float(event.get("duration"))
    if position <= 120 or _counts_as_finished(position, duration):
        _drop_progress(item, episode_parsed, filename)
        return
    seasons = _parsed_seasons(episode_parsed)
    episode_number = _as_int(episode_parsed.get("episode"))
    magnet = event.get("magnet") if isinstance(event.get("magnet"), str) else ""
    entry = {
        "position": position,
        "duration": duration,
        "at": when,
        "filename": filename,
        "magnet": magnet,
        "season": seasons[0] if len(seasons) == 1 else None,
        "episode": episode_number if len(seasons) == 1 else None,
    }
    if _progress_superseded(item, entry):
        _drop_progress(item, episode_parsed, filename)
        return
    media_type = str(item.get("media_type") or "")
    progress = [existing for existing in item.get("progress") or [] if isinstance(existing, dict)]
    progress = [
        existing for existing in progress
        if not _progress_matches(existing, episode_parsed, filename, media_type)
    ]
    progress.append(entry)
    item["progress"] = progress


def _runtime_seconds(client: TMDBClient, item: dict[str, Any], entry: dict[str, Any]) -> float:
    """Episode or movie length from TMDB, used when the file duration was not saved."""
    try:
        if item.get("media_type") == "movie":
            details = client.get_movie_details(int(item["tmdb_id"]))
            runtime = details.get("runtime") if isinstance(details, dict) else None
            return float(runtime) * 60 if isinstance(runtime, int) and runtime > 0 else 0
        season = _as_int(entry.get("season"))
        episode = _as_int(entry.get("episode"))
        if season is None or episode is None:
            return 0
        payload = client.get_tv_season(int(item["tmdb_id"]), season)
        for details in (payload or {}).get("episodes") or []:
            if isinstance(details, dict) and details.get("episode_number") == episode:
                runtime = details.get("runtime")
                return float(runtime) * 60 if isinstance(runtime, int) and runtime > 0 else 0
    except Exception:
        return 0
    return 0


def _keep_watching(items: list[dict[str, Any]], client: TMDBClient | None = None) -> list[dict[str, Any]]:
    """Unfinished plays from the last 14 days, one card per title, newest first."""
    cutoff = int(time.time() * 1000) - 14 * 24 * 60 * 60 * 1000
    cards = []
    for item in items:
        progress = item.get("progress")
        if not isinstance(progress, list):
            continue
        current = []
        for entry in progress:
            if not isinstance(entry, dict):
                continue
            position = _as_float(entry.get("position"))
            duration = _as_float(entry.get("duration"))
            at = _as_int(entry.get("at")) or 0
            if at < cutoff or position <= 120 or _counts_as_finished(position, duration):
                continue
            if _progress_superseded(item, entry):
                continue
            current.append(entry)
        if not current:
            continue
        latest = max(current, key=lambda entry: int(entry.get("at") or 0))
        card = _card(item)
        season = _as_int(latest.get("season"))
        episode = _as_int(latest.get("episode"))
        if item.get("media_type") == "tv" and season is not None and episode is not None:
            card["subtitle"] = _episode_label(season, episode)
        magnet = latest.get("magnet") if isinstance(latest.get("magnet"), str) and latest.get("magnet") else None
        filename = latest.get("filename") if isinstance(latest.get("filename"), str) and latest.get("filename") else None
        position = _as_float(latest.get("position"))
        duration = _as_float(latest.get("duration"))
        if duration <= 0 and client is not None:
            duration = _runtime_seconds(client, item, latest)
        card["minutes_left"] = _minutes_left(position, duration)
        card["magnet"] = magnet
        card["filename"] = filename
        card["_at"] = int(latest.get("at") or 0)
        cards.append(card)
    cards.sort(key=lambda card: int(card.get("_at") or 0), reverse=True)
    for card in cards:
        card.pop("_at", None)
    return cards


def _episode_label(season: int, episode: int) -> str:
    return f"Season {season} - Episode {episode}"


def _subtitle(item: dict[str, Any]) -> str | None:
    if item.get("media_type") == "tv":
        episodes = [episode for episode in item.get("watched_episodes") or [] if isinstance(episode, dict)]
        if episodes:
            latest = max(episodes, key=lambda episode: int(episode.get("at") or 0))
            season = _as_int(latest.get("season"))
            episode = _as_int(latest.get("episode"))
            if season is not None and episode is not None:
                return _episode_label(season, episode)
    year = _as_int(item.get("year"))
    return str(year) if year else None


def _card(item: dict[str, Any], rank: int | None = None) -> dict[str, Any]:
    year = _as_int(item.get("year"))
    return {
        "tmdb_id": item.get("tmdb_id"),
        "media_type": item.get("media_type"),
        "title": item.get("title") or "",
        "year": year,
        "poster_url": item.get("poster_url"),
        "backdrop_url": item.get("backdrop_url"),
        "subtitle": _subtitle(item) if rank is None else None,
        "rank": rank,
        "watched_at": item.get("watched_at"),
        "watched_episodes": item.get("watched_episodes") or [],
    }


def _upcoming_air_date(details: dict[str, Any]) -> str | None:
    """Air date of the next episode, when that date is today or later."""
    episode = details.get("next_episode_to_air")
    if not isinstance(episode, dict):
        return None
    air_date = episode.get("air_date")
    if not isinstance(air_date, str) or not air_date:
        return None
    try:
        released = date.fromisoformat(air_date)
    except ValueError:
        return None
    if released < date.today():
        return None
    return air_date


def _watched_is_last_aired(item: dict[str, Any], details: dict[str, Any]) -> bool:
    """True when the latest watched episode is the latest one that has aired."""
    episodes = [episode for episode in item.get("watched_episodes") or [] if isinstance(episode, dict)]
    if not episodes:
        return False
    latest = max(episodes, key=lambda episode: int(episode.get("at") or 0))
    season = _as_int(latest.get("season"))
    episode_number = _as_int(latest.get("episode"))
    aired = details.get("last_episode_to_air")
    if season is None or episode_number is None or not isinstance(aired, dict):
        return False
    return (
        season == _as_int(aired.get("season_number"))
        and episode_number == _as_int(aired.get("episode_number"))
    )


def _annotate_next_air(
    cards: list[dict[str, Any]],
    client: TMDBClient,
    cache: dict[int, dict[str, Any] | None],
    caught_up_only: bool,
) -> None:
    for card in cards:
        if card.get("media_type") != "tv":
            continue
        tmdb_id = _as_int(card.get("tmdb_id"))
        if tmdb_id is None:
            continue
        if tmdb_id not in cache:
            try:
                details = client.get_tv_details(tmdb_id)
            except Exception:
                details = None
            cache[tmdb_id] = details if isinstance(details, dict) else None
        details = cache[tmdb_id]
        if not details:
            continue
        if caught_up_only and not _watched_is_last_aired(card, details):
            continue
        air_date = _upcoming_air_date(details)
        if air_date:
            card["next_air_date"] = air_date


def _is_adult_details(details: dict[str, Any]) -> bool:
    return details.get("adult") is True or details.get("softcore") is True


def _classify_adult_activity(client: TMDBClient) -> None:
    """Fill in the adult flag for activity recorded before TMDB was checked."""
    pending = stats.unclassified_titles()
    if not pending:
        return
    data = _load()
    identities = data.get("identities", {})
    changed = False
    for media_type, tmdb_id in pending:
        try:
            details = client.get_tv_details(tmdb_id) if media_type == "tv" else client.get_movie_details(tmdb_id)
        except Exception:
            details = None
        if not isinstance(details, dict) or not details:
            continue
        adult = _is_adult_details(details)
        stats.set_adult(media_type, tmdb_id, adult)
        for identity in identities.values():
            if not isinstance(identity, dict):
                continue
            if identity.get("media_type") == media_type and identity.get("tmdb_id") == tmdb_id and identity.get("adult") is not adult:
                identity["adult"] = adult
                changed = True
    if changed:
        _save(data)


def _prune_superseded_progress() -> None:
    """Drop unfinished plays that a later finish already replaced."""
    data = _load()
    titles = data.get("titles")
    if not isinstance(titles, dict):
        return
    changed = False
    for item in titles.values():
        if not isinstance(item, dict) or not isinstance(item.get("progress"), list):
            continue
        kept = [
            entry for entry in item["progress"]
            if isinstance(entry, dict) and not _progress_superseded(item, entry)
        ]
        if len(kept) != len(item["progress"]):
            item["progress"] = kept
            changed = True
    if changed:
        _save(data)


def home() -> dict[str, Any]:
    """Recently watched titles plus trending series and movie charts."""
    _prune_superseded_progress()
    titles = catalog()
    recent = []
    for item in titles:
        if item.get("watched_at") or item.get("watched_episodes"):
            recent.append(_card(item))
    client = TMDBClient(settings.TMDB_API_KEY) if settings.TMDB_API_KEY else None
    keep_watching = _keep_watching(titles, client)
    if client is not None:
        _classify_adult_activity(client)
    series = stats.top("tv")
    movies = stats.top("movie")
    if client is not None:
        cache: dict[int, dict[str, Any] | None] = {}
        _annotate_next_air(recent, client, cache, caught_up_only=True)
        _annotate_next_air(series, client, cache, caught_up_only=False)
    return {"keep_watching": keep_watching, "recent": recent, "series": series, "movies": movies}


def refresh_artwork() -> None:
    """Fill in backdrop images for titles resolved before artwork was stored."""
    data = _load()
    changed = False
    for identity in data.get("identities", {}).values():
        if not isinstance(identity, dict) or not identity.get("tmdb_id") or identity.get("backdrop_url"):
            continue
        resolved = _resolve_identity(str(identity.get("title") or ""))
        if not resolved or not resolved.get("backdrop_url"):
            continue
        identity["backdrop_url"] = resolved["backdrop_url"]
        if resolved.get("poster_url") and not identity.get("poster_url"):
            identity["poster_url"] = resolved["poster_url"]
        catalog_key = f"{identity['media_type']}:{identity['tmdb_id']}"
        item = data.get("titles", {}).get(catalog_key)
        if isinstance(item, dict):
            item["backdrop_url"] = identity["backdrop_url"]
            if identity.get("poster_url") and not item.get("poster_url"):
                item["poster_url"] = identity["poster_url"]
        try:
            stats.update_artwork(
                identity["media_type"],
                identity["tmdb_id"],
                identity.get("poster_url"),
                identity.get("backdrop_url"),
            )
        except Exception:
            pass
        changed = True
    if changed:
        _save(data)


def catalog() -> list[dict[str, Any]]:
    """Titles already resolved, newest activity first."""
    titles = _load().get("titles")
    if not isinstance(titles, dict):
        return []
    items = [item for item in titles.values() if isinstance(item, dict)]
    items.sort(key=lambda item: int(item.get("updated_at") or 0), reverse=True)
    return items


def _worker() -> None:
    try:
        refresh_artwork()
    except Exception:
        pass
    while True:
        event = _queue.get()
        try:
            process_event(event)
        except Exception:
            pass
        finally:
            _queue.task_done()


def start() -> None:
    """Start the single background worker. Further calls do nothing."""
    global _started
    with _start_lock:
        if _started:
            return
        threading.Thread(target=_worker, name="library", daemon=True).start()
        _started = True


def enqueue(events: list[dict[str, Any]]) -> int:
    """Queue events and return how many were accepted. Does not wait for TMDB."""
    start()
    queued = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        title = event.get("title") if isinstance(event.get("title"), str) else ""
        filename = event.get("filename") if isinstance(event.get("filename"), str) else ""
        if not title.strip() and not filename.strip():
            continue
        _queue.put(event)
        queued += 1
    return queued
