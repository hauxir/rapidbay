import os
import tempfile
import time
from unittest.mock import patch

from app.library import catalog, process_event
from app.stats import adult_counts, record, top


def _show(results, _key):
    title = results[0]["title"]
    if "Dune" in title:
        return {
            "groups": [{
                "tmdb_id": 438631,
                "media_type": "movie",
                "title": "Dune",
                "year": 2021,
                "poster_url": "https://image.example/dune.jpg",
                "backdrop_url": "https://image.example/dune-bg.jpg",
            }],
            "other": [],
        }
    return {
        "groups": [{
            "tmdb_id": 95480,
            "media_type": "tv",
            "title": "Slow Horses",
            "year": 2022,
            "poster_url": "https://image.example/slow.jpg",
            "backdrop_url": "https://image.example/slow-bg.jpg",
        }],
        "other": [],
    }


def test_trending_chart_counts_watches_and_downloads_not_searches() -> None:
    now = int(time.time() * 1000)
    last_week = now - 7 * 24 * 60 * 60 * 1000
    too_old = now - 40 * 24 * 60 * 60 * 1000
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.stats.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show):
        process_event({
            "event": "search",
            "title": "Dune",
            "ts": now,
        })
        process_event({
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E01.mkv",
            "filename": "Slow.Horses.S06E01.mkv",
            "ts": now,
        })
        record(
            "download",
            {"tmdb_id": 100, "media_type": "tv", "title": "Recent Show", "year": 1999},
            last_week,
            "download:tv:100:recent",
        )
        record(
            "download",
            {"tmdb_id": 200, "media_type": "tv", "title": "Old Show", "year": 1990},
            too_old,
            "download:tv:200:old",
        )

        assert catalog()[0]["tmdb_id"] == 95480
        assert all(item["tmdb_id"] != 438631 for item in catalog())
        series = top("tv")
        movies = top("movie")
        assert [item["title"] for item in series] == ["Slow Horses", "Recent Show"]
        assert series[0]["rank"] == 1
        assert series[0]["backdrop_url"] == "https://image.example/slow-bg.jpg"
        assert movies == []
        assert all(item["title"] != "Old Show" for item in series)


def test_adult_titles_stay_out_of_trending_and_are_counted_apart() -> None:
    now = int(time.time() * 1000)
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.stats.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")):
        record(
            "watched",
            {"tmdb_id": 95480, "media_type": "tv", "title": "Slow Horses", "adult": False},
            now,
            "watched:tv:95480:6:1",
        )
        record(
            "download",
            {"tmdb_id": 77, "media_type": "movie", "title": "Adult Film", "adult": True},
            now,
            "download:movie:77:hash",
        )
        record(
            "search",
            {"tmdb_id": 77, "media_type": "movie", "title": "Adult Film", "adult": True},
            now,
            "search:movie:77:adult",
        )

        assert [item["title"] for item in top("tv")] == ["Slow Horses"]
        assert top("movie") == []
        assert adult_counts() == {"tv": 0, "movie": 1}
