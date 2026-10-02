"""Search, download, and watch counts in a single SQLite file."""

import json
import os
import sqlite3
import threading
import time
from typing import Any

import settings

_lock = threading.Lock()
_ready_path: str | None = None

_SCORES = {"watched": 3, "download": 2, "search": 1}


def _path() -> str:
    directory = os.path.dirname(settings.LIBRARY_PATH) or "."
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "stats.db")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_path(), timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def _trending_since_ms() -> int:
    """Rolling window for the home charts. Not limited to the current day."""
    return int(time.time() * 1000) - 30 * 24 * 60 * 60 * 1000


def init() -> None:
    """Create the stats file and import existing library activity once."""
    global _ready_path
    with _lock:
        path = _path()
        if _ready_path == path and os.path.exists(path):
            return
        with _connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS activity (
                    id INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL,
                    media_type TEXT,
                    tmdb_id INTEGER,
                    title TEXT,
                    year INTEGER,
                    poster_url TEXT,
                    backdrop_url TEXT,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(activity)")}
            if "adult" not in columns:
                connection.execute("ALTER TABLE activity ADD COLUMN adult INTEGER")
            imported = connection.execute(
                "SELECT value FROM meta WHERE key = 'library_imported'"
            ).fetchone()
            if imported is None:
                _import_library(connection)
                connection.execute(
                    "INSERT INTO meta (key, value) VALUES ('library_imported', '1')"
                )
        _ready_path = path


def _import_library(connection: sqlite3.Connection) -> None:
    library_path = settings.LIBRARY_PATH
    try:
        with open(library_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return
    titles = data.get("titles") if isinstance(data, dict) else None
    if not isinstance(titles, dict):
        return
    for item in titles.values():
        if not isinstance(item, dict) or not isinstance(item.get("tmdb_id"), int):
            continue
        for download in item.get("downloads") or []:
            if not isinstance(download, dict):
                continue
            digest = download.get("hash") or ""
            record(
                "download",
                item,
                int(download.get("at") or 0),
                f"download:{item['media_type']}:{item['tmdb_id']}:{digest}",
                connection=connection,
            )
        if item.get("media_type") == "movie" and item.get("watched_at"):
            record(
                "watched",
                item,
                int(item.get("watched_at") or 0),
                f"watched:{item['media_type']}:{item['tmdb_id']}",
                connection=connection,
            )
        for episode in item.get("watched_episodes") or []:
            if not isinstance(episode, dict):
                continue
            record(
                "watched",
                item,
                int(episode.get("at") or 0),
                f"watched:{item['media_type']}:{item['tmdb_id']}:{episode.get('season')}:{episode.get('episode')}",
                connection=connection,
            )


def record(
    kind: str,
    identity: dict[str, Any],
    when: int,
    dedupe_key: str,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Store one activity row. Repeated keys are ignored."""
    tmdb_id = identity.get("tmdb_id")
    media_type = identity.get("media_type")
    if kind not in _SCORES or not isinstance(tmdb_id, int) or media_type not in ("tv", "movie"):
        return
    if not dedupe_key:
        return
    year = identity.get("year")
    try:
        year = int(year) if year else None
    except (TypeError, ValueError):
        year = None
    adult_flag = identity.get("adult")
    adult = 1 if adult_flag is True else 0 if adult_flag is False else None
    payload = (
        kind,
        media_type,
        tmdb_id,
        identity.get("title") or "",
        year,
        identity.get("poster_url"),
        identity.get("backdrop_url"),
        dedupe_key,
        int(when or 0),
        adult,
    )
    statement = """
        INSERT OR IGNORE INTO activity (
            kind, media_type, tmdb_id, title, year, poster_url, backdrop_url, dedupe_key, created_at, adult
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    if connection is not None:
        connection.execute(statement, payload)
        return
    init()
    with _lock, _connect() as owned:
        owned.execute(statement, payload)


def update_artwork(media_type: str, tmdb_id: int, poster_url: str | None, backdrop_url: str | None) -> None:
    if not backdrop_url and not poster_url:
        return
    init()
    with _lock, _connect() as connection:
        connection.execute(
            """
            UPDATE activity
            SET poster_url = COALESCE(?, poster_url),
                backdrop_url = COALESCE(?, backdrop_url)
            WHERE media_type = ? AND tmdb_id = ?
            """,
            (poster_url, backdrop_url, media_type, tmdb_id),
        )


def top(media_type: str, limit: int = 10) -> list[dict[str, Any]]:
    """Highest scoring downloads and finished watches from the last 30 days. Searches are ignored."""
    init()
    with _lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT a.media_type, a.tmdb_id, a.title, a.year, a.poster_url, a.backdrop_url, s.score
            FROM activity a
            JOIN (
                SELECT media_type, tmdb_id,
                       SUM(CASE kind WHEN 'watched' THEN 3 WHEN 'download' THEN 2 ELSE 0 END) AS score,
                       MAX(id) AS latest_id
                FROM activity
                WHERE created_at >= ? AND media_type = ? AND tmdb_id IS NOT NULL
                  AND kind IN ('watched', 'download') AND IFNULL(adult, 0) = 0
                GROUP BY media_type, tmdb_id
            ) s ON a.id = s.latest_id
            ORDER BY s.score DESC, a.created_at DESC
            LIMIT ?
            """,
            (_trending_since_ms(), media_type, limit),
        ).fetchall()
    cards = []
    for rank, row in enumerate(rows, start=1):
        cards.append({
            "tmdb_id": row["tmdb_id"],
            "media_type": row["media_type"],
            "title": row["title"],
            "year": row["year"],
            "poster_url": row["poster_url"],
            "backdrop_url": row["backdrop_url"],
            "subtitle": None,
            "rank": rank,
        })
    return cards


def unclassified_titles() -> list[tuple[str, int]]:
    """Titles recorded before we knew whether TMDB marks them adult."""
    init()
    with _lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT media_type, tmdb_id
            FROM activity
            WHERE adult IS NULL AND tmdb_id IS NOT NULL AND media_type IN ('tv', 'movie')
            """
        ).fetchall()
    return [(row["media_type"], int(row["tmdb_id"])) for row in rows]


def set_adult(media_type: str, tmdb_id: int, adult: bool) -> None:
    """Mark every activity row for a title. Adult rows stay out of the trending chart."""
    init()
    with _lock, _connect() as connection:
        connection.execute(
            """
            UPDATE activity
            SET adult = ?
            WHERE media_type = ? AND tmdb_id = ?
            """,
            (1 if adult else 0, media_type, tmdb_id),
        )


def adult_counts() -> dict[str, int]:
    """Distinct adult titles downloaded or finished in the trending window. Not shown on the home page."""
    init()
    counts = {"tv": 0, "movie": 0}
    with _lock, _connect() as connection:
        rows = connection.execute(
            """
            SELECT media_type, COUNT(DISTINCT tmdb_id) AS total
            FROM activity
            WHERE created_at >= ? AND adult = 1 AND kind IN ('watched', 'download')
              AND media_type IN ('tv', 'movie')
            GROUP BY media_type
            """,
            (_trending_since_ms(),),
        ).fetchall()
    for row in rows:
        counts[str(row["media_type"])] = int(row["total"])
    return counts


def search_dedupe_key(identity: dict[str, Any], query: str, when: int) -> str:
    stamp = int(when or time.time() * 1000) // 60000
    return f"search:{identity.get('media_type')}:{identity.get('tmdb_id')}:{query.casefold()}:{stamp}"
