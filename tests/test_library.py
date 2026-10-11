import contextlib
import json
import os
import tempfile
import time
from datetime import date, timedelta
from unittest.mock import patch

from app.library import catalog, home, present_watch_rows, process_event, watch_rows


def _show(results, _key):
    title = results[0]["title"]
    if "Slow Horses" in title or "Slow.Horses" in title:
        return {
            "groups": [{
                "tmdb_id": 95480,
                "media_type": "tv",
                "title": "Slow Horses",
                "year": 2022,
                "poster_url": "https://image.example/slow.jpg",
            }],
            "other": [],
        }
    if "Dune" in title:
        return {
            "groups": [{
                "tmdb_id": 438631,
                "media_type": "movie",
                "title": "Dune",
                "year": 2021,
                "poster_url": None,
            }],
            "other": [],
        }
    return {"groups": [], "other": []}


def test_watched_episode_is_stored_under_the_show_id() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show) as enrich:
        process_event({
            "event": "download",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow Horses S06",
            "filename": "",
            "ts": 10,
        })
        process_event({
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": 20,
        })
        process_event({
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": 30,
        })
        assert enrich.call_count == 1
        stored = catalog()
        assert stored[0]["tmdb_id"] == 95480
        assert stored[0]["media_type"] == "tv"
        assert stored[0]["downloads"] == [{"hash": "abc", "label": "Slow Horses S06", "at": 10}]
        assert stored[0]["watched_episodes"] == []
        with patch("app.library.settings.TMDB_API_KEY", None):
            rows = watch_rows([
                {
                    "event": "watched",
                    "magnet": "magnet:?xt=urn:btih:abc",
                    "title": "Slow.Horses.S06E02.mkv",
                    "filename": "Slow.Horses.S06E02.mkv",
                    "ts": 20,
                },
                {
                    "event": "watched",
                    "magnet": "magnet:?xt=urn:btih:abc",
                    "title": "Slow.Horses.S06E02.mkv",
                    "filename": "Slow.Horses.S06E02.mkv",
                    "ts": 30,
                },
            ])
        assert rows["recent"][0]["watched_episodes"] == [{
            "season": 6,
            "episode": 2,
            "filename": "Slow.Horses.S06E02.mkv",
            "at": 30,
        }]
        assert catalog()[0]["watched_episodes"] == []


def test_watched_movie_is_stored_under_the_movie_id() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show):
        process_event({
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:def",
            "title": "Dune.2021.1080p.mkv",
            "filename": "Dune.2021.1080p.mkv",
            "ts": 5,
        })
        assert catalog() == []
        rows = watch_rows([{
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:def",
            "title": "Dune.2021.1080p.mkv",
            "filename": "Dune.2021.1080p.mkv",
            "ts": 5,
        }])
        assert rows["recent"][0]["tmdb_id"] == 438631
        assert rows["recent"][0]["media_type"] == "movie"
        assert rows["recent"][0]["watched_at"] == 5
        with open(os.path.join(tmp, "library.json"), encoding="utf-8") as handle:
            on_disk = json.load(handle)
        assert "titles" not in on_disk or "movie:438631" not in on_disk["titles"]


def test_season_pack_does_not_mark_episodes_watched() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show):
        process_event({
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow Horses 2022 Seasons 1 to 5 Complete 1080p",
            "filename": "Slow Horses 2022 Seasons 1 to 5 Complete 1080p",
            "ts": 8,
        })
        assert catalog() == []
        assert watch_rows([{
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow Horses 2022 Seasons 1 to 5 Complete 1080p",
            "filename": "Slow Horses 2022 Seasons 1 to 5 Complete 1080p",
            "ts": 8,
        }])["recent"] == []


def test_unmatched_title_is_not_added_to_the_catalog() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.failure_count", return_value=0), \
            patch("app.library._resolve_identity_direct", return_value=None), \
            patch("app.library.enrich_search_results", side_effect=_show) as enrich:
        process_event({
            "event": "download",
            "magnet": "magnet:?xt=urn:btih:fff",
            "title": "Totally Unknown Audiobook",
            "ts": 1,
        })
        process_event({
            "event": "download",
            "magnet": "magnet:?xt=urn:btih:fff",
            "title": "Totally Unknown Audiobook",
            "ts": 2,
        })
        assert enrich.call_count == 1
        assert catalog() == []


def test_next_air_date_follows_catch_up_on_recent_and_any_upcoming_on_the_chart() -> None:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    details = {
        1: {
            "last_episode_to_air": {"season_number": 2, "episode_number": 2},
            "next_episode_to_air": {"air_date": tomorrow},
        },
        2: {
            "last_episode_to_air": {"season_number": 2, "episode_number": 2},
            "next_episode_to_air": {"air_date": tomorrow},
        },
        3: {
            "last_episode_to_air": {"season_number": 6, "episode_number": 6},
            "next_episode_to_air": {"air_date": yesterday},
        },
        4: {
            "last_episode_to_air": {"season_number": 10, "episode_number": 18},
            "next_episode_to_air": None,
        },
    }

    class FakeClient:
        def __init__(self, _key: str) -> None:
            return None

        def get_tv_details(self, tv_id: int) -> dict:
            return details[tv_id]

    stored = [
        {"tmdb_id": 1, "media_type": "tv", "title": "Caught Up", "watched_episodes": [{"season": 2, "episode": 2, "at": 5}]},
        {"tmdb_id": 2, "media_type": "tv", "title": "Behind", "watched_episodes": [{"season": 2, "episode": 1, "at": 5}]},
        {"tmdb_id": 3, "media_type": "tv", "title": "Past Date", "watched_episodes": [{"season": 6, "episode": 6, "at": 5}]},
        {"tmdb_id": 4, "media_type": "tv", "title": "Ended", "watched_episodes": [{"season": 10, "episode": 18, "at": 5}]},
        {"tmdb_id": 9, "media_type": "movie", "title": "Film", "watched_at": 5, "watched_episodes": []},
    ]
    series = [
        {"tmdb_id": 2, "media_type": "tv", "title": "Behind", "rank": 1},
        {"tmdb_id": 4, "media_type": "tv", "title": "Ended", "rank": 2},
    ]
    with patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.stats.top", side_effect=lambda media: series if media == "tv" else []), \
            patch("app.library.TMDBClient", FakeClient):
        payload = present_watch_rows(stored)
        payload["series"] = home()["series"]

    recent = {item["title"]: item.get("next_air_date") for item in payload["recent"]}
    assert recent["Caught Up"] == tomorrow
    assert recent["Behind"] is None
    assert recent["Past Date"] is None
    assert recent["Ended"] is None
    assert recent["Film"] is None
    chart = {item["title"]: item.get("next_air_date") for item in payload["series"]}
    assert chart["Behind"] == tomorrow
    assert chart["Ended"] is None


def test_keep_watching_lists_unfinished_plays_from_the_last_two_weeks() -> None:
    now = int(time.time() * 1000)
    old = now - 15 * 24 * 60 * 60 * 1000
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show):
        too_short = {
            "event": "progress",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": now,
            "position": 90,
            "duration": 2700,
        }
        assert watch_rows([too_short])["keep_watching"] == []

        playing = [
            {
                "event": "progress",
                "magnet": "magnet:?xt=urn:btih:abc",
                "title": "Slow.Horses.S06E01.mkv",
                "filename": "Slow.Horses.S06E01.mkv",
                "ts": old,
                "position": 400,
                "duration": 2700,
            },
            {
                "event": "progress",
                "magnet": "magnet:?xt=urn:btih:abc",
                "title": "Slow.Horses.S06E02.mkv",
                "filename": "Slow.Horses.S06E02.mkv",
                "ts": now,
                "position": 300,
                "duration": 2700,
            },
            {
                "event": "progress",
                "magnet": "magnet:?xt=urn:btih:def",
                "title": "Dune.2021.1080p.mkv",
                "filename": "Dune.2021.1080p.mkv",
                "ts": now,
                "position": 2650,
                "duration": 2700,
            },
        ]
        with patch("app.library.settings.TMDB_API_KEY", None):
            cards = watch_rows(playing)["keep_watching"]
        assert [card["title"] for card in cards] == ["Slow Horses"]
        assert cards[0]["subtitle"] == "Season 6 - Episode 2"
        assert cards[0]["minutes_left"] == 40
        assert cards[0]["filename"] == "Slow.Horses.S06E02.mkv"
        assert catalog() == []

        with patch("app.library.settings.TMDB_API_KEY", None):
            finished = watch_rows(playing + [{
                "event": "watched",
                "magnet": "magnet:?xt=urn:btih:abc",
                "title": "Slow.Horses.S06E02.mkv",
                "filename": "Slow.Horses.S06E02.mkv",
                "ts": now,
            }])
        assert finished["keep_watching"] == []


def test_finish_removes_an_earlier_unfinished_play_but_keeps_a_later_rewatch() -> None:
    now = int(time.time() * 1000)
    earlier = now - 60 * 60 * 1000
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show):
        started = {
            "event": "progress",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": earlier,
            "position": 400,
            "duration": 2700,
        }
        finished = {
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": now,
        }
        leftover = {
            "event": "progress",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": now + 1000,
            "position": 180,
            "duration": 0,
        }
        watch_rows([started])
        with patch("app.library.settings.TMDB_API_KEY", None):
            hidden = watch_rows([started, finished, leftover])
        assert hidden["keep_watching"] == []
        assert hidden["recent"][0]["subtitle"] == "Season 6 - Episode 2"

        rewatch = {
            "event": "progress",
            "magnet": "magnet:?xt=urn:btih:abc",
            "title": "Slow.Horses.S06E02.mkv",
            "filename": "Slow.Horses.S06E02.mkv",
            "ts": now + 2000,
            "position": 300,
            "duration": 2700,
        }
        with patch("app.library.settings.TMDB_API_KEY", None):
            shown = watch_rows([started, finished, leftover, rewatch])
        assert [card["title"] for card in shown["keep_watching"]] == ["Slow Horses"]
        assert shown["keep_watching"][0]["minutes_left"] == 40
        assert shown["recent"][0]["subtitle"] == "Season 6 - Episode 2"


def test_keep_watching_lists_every_unfinished_episode() -> None:
    now = int(time.time() * 1000)
    earlier = now - 60 * 60 * 1000
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show):
        playing = [
            {
                "event": "progress",
                "magnet": "magnet:?xt=urn:btih:abc",
                "title": "Slow.Horses.S06E01.mkv",
                "filename": "Slow.Horses.S06E01.mkv",
                "ts": earlier,
                "position": 400,
                "duration": 2700,
            },
            {
                "event": "progress",
                "magnet": "magnet:?xt=urn:btih:abc",
                "title": "Slow.Horses.S06E02.mkv",
                "filename": "Slow.Horses.S06E02.mkv",
                "ts": now,
                "position": 300,
                "duration": 2700,
            },
        ]
        cards = watch_rows(playing)["keep_watching"]

    assert [card["filename"] for card in cards] == [
        "Slow.Horses.S06E02.mkv",
        "Slow.Horses.S06E01.mkv",
    ]
    assert [card["subtitle"] for card in cards] == [
        "Season 6 - Episode 2",
        "Season 6 - Episode 1",
    ]


def test_finished_movie_without_a_date_stays_in_recently_watched() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.enrich_search_results", side_effect=_show), \
            patch("app.library.stats.record") as record:
        process_event({
            "event": "watched",
            "magnet": "magnet:?xt=urn:btih:def",
            "title": "Dune.2021.1080p.mkv",
            "filename": "Dune.2021.1080p.mkv",
            "ts": 0,
        })
        record.assert_not_called()
        with patch("app.library.settings.TMDB_API_KEY", None):
            rows = watch_rows([{
                "event": "watched",
                "magnet": "magnet:?xt=urn:btih:def",
                "title": "Dune.2021.1080p.mkv",
                "filename": "Dune.2021.1080p.mkv",
                "ts": 0,
            }])

    assert [item["title"] for item in rows["recent"]] == ["Dune"]
    assert rows["recent"][0]["watched_at"] == 0


def _no_match(_results, _key):
    return {"groups": [], "other": []}


def _download(ts: int) -> dict:
    return {
        "event": "download",
        "magnet": "magnet:?xt=urn:btih:fff",
        "title": "Totally Unknown Audiobook",
        "ts": ts,
    }


def test_tmdb_failure_does_not_leave_an_unmatched_marker() -> None:
    failures = iter([0, 1, 1, 1])
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.failure_count", side_effect=lambda: next(failures)), \
            patch("app.library.enrich_search_results", side_effect=_no_match) as enrich, \
            patch("app.library._resolve_identity_direct", return_value=None):
        process_event(_download(1))
        assert not os.path.exists(os.path.join(tmp, "library.json"))
        # TMDB is back: the same title is looked up again, not skipped.
        with patch("app.library.failure_count", return_value=0):
            process_event(_download(2))
        assert enrich.call_count == 2


def test_confirmed_no_match_is_remembered_with_a_time_and_retried_after_a_day() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.failure_count", return_value=0), \
            patch("app.library.enrich_search_results", side_effect=_no_match) as enrich, \
            patch("app.library._resolve_identity_direct", return_value=None):
        process_event(_download(1))
        process_event(_download(2))
        assert enrich.call_count == 1
        with open(os.path.join(tmp, "library.json"), encoding="utf-8") as handle:
            marker = next(iter(json.load(handle)["identities"].values()))
        assert marker["unmatched"] is True
        assert marker["at"] > 0

        with patch("app.library.time.time", return_value=time.time() + 25 * 60 * 60):
            process_event(_download(3))
        assert enrich.call_count == 2


def test_unmatched_marker_without_a_time_is_retried() -> None:
    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.failure_count", return_value=0), \
            patch("app.library.enrich_search_results", side_effect=_no_match) as enrich, \
            patch("app.library._resolve_identity_direct", return_value=None):
        process_event(_download(1))
        path = os.path.join(tmp, "library.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        for key in data["identities"]:
            data["identities"][key] = {"unmatched": True}
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        process_event(_download(2))
        assert enrich.call_count == 2


def _movie_identity(_results, _key):
    return {
        "groups": [{"tmdb_id": 438631, "media_type": "movie", "title": "Dune", "year": 2021, "poster_url": None}],
        "other": [],
    }


def test_concurrent_downloads_all_reach_the_catalog() -> None:
    import threading

    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")), \
            patch("app.library.settings.TMDB_API_KEY", "key"), \
            patch("app.library.stats.record"), \
            patch("app.library.enrich_search_results", side_effect=_movie_identity):
        errors: list[BaseException] = []

        def download(index: int) -> None:
            try:
                process_event({
                    "event": "download",
                    "magnet": f"magnet:?xt=urn:btih:hash{index}",
                    "title": "Dune 2021 1080p",
                    "ts": index + 1,
                })
            except BaseException as error:
                errors.append(error)

        threads = [threading.Thread(target=download, args=(index,)) for index in range(24)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        assert len(catalog()[0]["downloads"]) == 24
        assert [name for name in os.listdir(tmp) if name.endswith(".tmp")] == []


def test_failed_save_leaves_no_temporary_file_and_keeps_the_old_catalog() -> None:
    from app.library import _load, _save

    with tempfile.TemporaryDirectory() as tmp, \
            patch("app.library.settings.LIBRARY_PATH", os.path.join(tmp, "library.json")):
        _save({"identities": {}, "titles": {"a": {}}})
        with patch("app.library.json.dump", side_effect=OSError("disk full")), contextlib.suppress(OSError):
            _save({"identities": {}, "titles": {}})
        assert _load()["titles"] == {"a": {}}
        assert os.listdir(tmp) == ["library.json"]


def test_failed_event_is_logged_and_retried_then_dropped() -> None:
    from app import library

    event = {"event": "download", "title": "Dune 2021", "ts": 1}
    with patch("app.library.process_event", side_effect=RuntimeError("boom")), \
            patch("app.library.log.debug") as debug, \
            patch("app.library.log.write_log") as write_log, \
            patch("app.library.threading.Timer") as timer:
        library._handle(event)
        retried = timer.call_args.kwargs["args"][0]
        assert retried["_attempts"] == 1
        assert timer.call_args.args[0] == library._RETRY_DELAY_SECONDS
        timer.return_value.start.assert_called_once()

        library._handle(retried)
        second = timer.call_args.kwargs["args"][0]
        assert second["_attempts"] == 2
        assert timer.call_args.args[0] == library._RETRY_DELAY_SECONDS * 2

        timer.reset_mock()
        library._handle(second)
        timer.assert_not_called()

    assert write_log.call_count == 3
    assert "dropped" in debug.call_args.args[0]


def test_successful_event_is_not_retried() -> None:
    from app import library

    with patch("app.library.process_event") as process, \
            patch("app.library.threading.Timer") as timer:
        library._handle({"event": "download", "title": "Dune"})

    process.assert_called_once()
    timer.assert_not_called()
