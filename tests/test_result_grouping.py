from datetime import date
from unittest.mock import MagicMock, call, patch

from app.result_grouping import MAX_TMDB_LOOKUPS, enrich_search_results, season_episode_details


def parsed_title(title: str) -> dict[str, object]:
    """Provide predictable parser output for torrent fixtures."""
    pieces = title.split("|")
    return {
        "title": pieces[0],
        "season": int(pieces[1]) if len(pieces) > 1 and pieces[1] else None,
        "episode": int(pieces[2]) if len(pieces) > 2 and pieces[2] else None,
        "year": int(pieces[3]) if len(pieces) > 3 and pieces[3] else None,
    }


def make_torrent(title: str, seeds: int = 10) -> dict[str, object]:
    return {"title": title, "seeds": seeds, "magnet": f"magnet:?xt={seeds}"}


def test_no_tmdb_key_returns_all_results_as_other_with_parsed_title() -> None:
    results = [make_torrent("The Matrix|"), make_torrent("Breaking Bad|1|1")]
    with patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)):
        response = enrich_search_results(results, None)

    assert response["groups"] == []
    assert response["other"] == [
        {**results[0], "parsed_title": "The Matrix"},
        {**results[1], "parsed_title": "Breaking Bad"},
    ]


def test_movie_match_builds_group_and_preserves_original_torrent_fields() -> None:
    result = make_torrent("The Matrix|", seeds=51)
    client = MagicMock()
    client.search_multi.return_value = {
        "results": [{"id": 603, "media_type": "movie", "title": "The Matrix"}]
    }
    client.get_movie_details.return_value = {
        "id": 603,
        "title": "The Matrix",
        "release_date": "1999-03-30",
        "poster_path": "/matrix.jpg",
    }
    client.get_image_url.return_value = "https://image.tmdb.org/t/p/w185/matrix.jpg"

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    assert response["other"] == []
    assert response["groups"] == [
        {
            "tmdb_id": 603,
            "title": "The Matrix",
            "year": 1999,
            "poster_url": "https://image.tmdb.org/t/p/w185/matrix.jpg",
            "media_type": "movie",
            "seasons": [],
            "results": [result],
            "overview": None,
            "genres": [],
            "vote_average": None,
            "backdrop_url": None,
            "runtime": None,
        }
    ]


def test_tv_match_buckets_results_by_season_and_keeps_torrent_fields() -> None:
    first = make_torrent("Example Show|2|3", seeds=12)
    second = make_torrent("Example Show|1|8", seeds=22)
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    client.get_tv_details.return_value = {
        "id": 42,
        "name": "Example Show",
        "first_air_date": "2020-01-01",
    }

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([first, second], "api-key")

    group = response["groups"][0]
    assert group["media_type"] == "tv"
    assert group["year"] == 2020
    assert group["seasons"] == [
        {"season": 1, "episodes": [second]},
        {"season": 2, "episodes": [first]},
    ]
    assert response["other"] == []


def test_movie_group_includes_plot_genres_rating_runtime_and_backdrop() -> None:
    result = make_torrent("Dune|||2021")
    client = MagicMock()
    client.search_multi.return_value = {
        "results": [{"id": 438631, "media_type": "movie", "title": "Dune", "release_date": "2021-09-15"}]
    }
    client.get_movie_details.return_value = {
        "id": 438631,
        "title": "Dune",
        "release_date": "2021-09-15",
        "overview": " Paul Atreides leaves Caladan. ",
        "genres": [{"name": "Science Fiction"}, {"name": "Adventure"}],
        "vote_average": 7.785,
        "vote_count": 100,
        "runtime": 155,
        "backdrop_path": "/dune.jpg",
        "poster_path": "/poster.jpg",
    }
    client.get_image_url.side_effect = lambda path, size="w185": f"https://image.tmdb.org/t/p/{size}{path}"

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    group = response["groups"][0]
    assert group["overview"] == "Paul Atreides leaves Caladan."
    assert group["genres"] == ["Science Fiction", "Adventure"]
    assert group["vote_average"] == 7.8
    assert group["runtime"] == 155
    assert group["backdrop_url"] == "https://image.tmdb.org/t/p/w780/dune.jpg"


def test_tv_group_includes_the_latest_aired_episode() -> None:
    result = make_torrent("Example Show|2|4")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    client.get_tv_details.return_value = {
        "id": 42,
        "name": "Example Show",
        "first_air_date": "2020-01-01",
        "last_episode_to_air": {
            "name": "  Old Scores ",
            "overview": " Lamb closes the file. ",
            "season_number": 2,
            "episode_number": 4,
            "air_date": "2026-09-23",
            "runtime": 48,
            "vote_average": 8.24,
            "vote_count": 20,
            "still_path": "/still.jpg",
        },
    }
    client.get_image_url.side_effect = lambda path, size="w185": f"https://image.tmdb.org/t/p/{size}{path}"

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
        patch("app.result_grouping.date") as clock,
    ):
        clock.today.return_value = date(2026, 9, 26)
        clock.fromisoformat.side_effect = date.fromisoformat
        response = enrich_search_results([result], "api-key")

    assert response["groups"][0]["latest_episode"] == {
        "name": "Old Scores",
        "overview": "Lamb closes the file.",
        "season_number": 2,
        "episode_number": 4,
        "air_date": "2026-09-23",
        "runtime": 48,
        "vote_average": 8.2,
        "still_url": "https://image.tmdb.org/t/p/w300/still.jpg",
    }
    assert response["groups"][0]["seasons"][0]["episodes"] == [result]


def test_latest_episode_older_than_two_weeks_is_omitted() -> None:
    result = make_torrent("Example Show|1|1")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    episode = {
        "name": "Old Scores",
        "season_number": 2,
        "episode_number": 4,
        "air_date": "2026-09-12",
    }
    client.get_tv_details.return_value = {
        "id": 42,
        "name": "Example Show",
        "first_air_date": "2020-01-01",
        "last_episode_to_air": episode,
    }

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
        patch("app.result_grouping.date") as clock,
    ):
        clock.today.return_value = date(2026, 9, 26)
        clock.fromisoformat.side_effect = date.fromisoformat
        too_old = enrich_search_results([result], "api-key")
        episode["air_date"] = "2026-09-13"
        recent = enrich_search_results([result], "api-key")

    assert "latest_episode" not in too_old["groups"][0]
    assert recent["groups"][0]["latest_episode"]["air_date"] == "2026-09-13"


def test_tv_group_without_a_latest_episode_omits_the_section() -> None:
    result = make_torrent("Example Show|1|1")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    client.get_tv_details.return_value = {
        "id": 42,
        "name": "Example Show",
        "first_air_date": "2020-01-01",
        "last_episode_to_air": None,
    }

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    assert "latest_episode" not in response["groups"][0]


def test_tv_group_includes_plot_genres_rating_and_backdrop() -> None:
    result = make_torrent("Example Show|1|1")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    client.get_tv_details.return_value = {
        "id": 42,
        "name": "Example Show",
        "first_air_date": "2020-01-01",
        "overview": "  A quiet office. ",
        "genres": [{"id": 1, "name": "Drama"}, {"name": " "}, "nope", {"name": "Comedy"}],
        "vote_average": 8.025,
        "vote_count": 12,
        "backdrop_path": "/back.jpg",
        "poster_path": "/poster.jpg",
    }
    client.get_image_url.side_effect = lambda path, size="w185": f"https://image.tmdb.org/t/p/{size}{path}"

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    group = response["groups"][0]
    assert group["overview"] == "A quiet office."
    assert group["genres"] == ["Drama", "Comedy"]
    assert group["vote_average"] == 8.0
    assert group["backdrop_url"] == "https://image.tmdb.org/t/p/w780/back.jpg"
    assert group["poster_url"] == "https://image.tmdb.org/t/p/w185/poster.jpg"


def test_groups_are_ordered_by_number_of_torrents() -> None:
    results = [
        make_torrent("Alpha Show|1|1", seeds=1),
        make_torrent("Zulu Movie|", seeds=2),
        make_torrent("Zulu Movie|", seeds=3),
        make_torrent("Zulu Movie|", seeds=4),
    ]
    client = MagicMock()
    client.search_multi.side_effect = [
        {"results": [{"id": 7, "media_type": "tv", "name": "Alpha Show"}]},
        {"results": [{"id": 8, "media_type": "movie", "title": "Zulu Movie"}]},
    ]
    client.get_tv_details.return_value = {"id": 7, "name": "Alpha Show"}
    client.get_movie_details.return_value = {"id": 8, "title": "Zulu Movie"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results(results, "api-key")

    assert [group["title"] for group in response["groups"]] == ["Zulu Movie", "Alpha Show"]


def test_title_without_tmdb_match_is_returned_in_other() -> None:
    result = make_torrent("Unknown Series|1|5")
    client = MagicMock()
    client.search_multi.return_value = {"results": []}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    assert response == {"groups": [], "other": [{**result, "parsed_title": "Unknown Series"}]}


def test_movie_match_falls_back_to_tv_details() -> None:
    result = make_torrent("A Show|1|2")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 123, "media_type": "movie"}]}
    client.get_movie_details.return_value = None
    client.get_tv_details.return_value = {"id": 123, "name": "A Show"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    client.get_movie_details.assert_called_once_with(123)
    client.get_tv_details.assert_called_once_with(123)
    assert response["groups"][0]["media_type"] == "tv"
    assert response["groups"][0]["seasons"][0]["episodes"] == [result]


def test_tmdb_lookups_are_capped_at_thirty_distinct_titles() -> None:
    results = [make_torrent(f"Series {index}|") for index in range(MAX_TMDB_LOOKUPS + 1)]
    client = MagicMock()
    client.search_multi.return_value = {"results": []}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results(results, "api-key")

    assert client.search_multi.call_count == MAX_TMDB_LOOKUPS
    assert len(response["other"]) == MAX_TMDB_LOOKUPS + 1


def test_tv_match_falls_back_to_movie_details() -> None:
    result = make_torrent("A Movie|")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 321, "media_type": "tv"}]}
    client.get_tv_details.return_value = None
    client.get_movie_details.return_value = {"id": 321, "title": "A Movie"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    client.get_tv_details.assert_called_once_with(321)
    client.get_movie_details.assert_called_once_with(321)
    group = response["groups"][0]
    assert group["media_type"] == "movie"
    assert group["seasons"] == []
    assert group["results"] == [result]


def test_tv_result_without_season_goes_to_other_instead_of_a_fake_bucket() -> None:
    result = make_torrent("Example Show|")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    client.get_tv_details.return_value = {"id": 42, "name": "Example Show"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    assert response["groups"] == []
    assert response["other"] == [{**result, "parsed_title": "Example Show"}]


def test_empty_tv_group_is_omitted_while_a_group_with_releases_remains() -> None:
    linked = make_torrent("Example Show|1|1")
    unlinked = make_torrent("Miniseries|")
    client = MagicMock()
    client.search_multi.side_effect = [
        {"results": [{"id": 42, "media_type": "tv"}]},
        {"results": [{"id": 99, "media_type": "tv"}]},
    ]
    client.get_tv_details.side_effect = lambda tmdb_id: (
        {"id": 42, "name": "Example Show"} if tmdb_id == 42 else {"id": 99, "name": "Miniseries"}
    )

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([linked, unlinked], "api-key")

    assert [group["title"] for group in response["groups"]] == ["Example Show"]
    assert response["groups"][0]["seasons"][0]["episodes"] == [linked]
    assert response["other"] == [{**unlinked, "parsed_title": "Miniseries"}]


def test_tv_episodes_are_sorted_by_episode_and_missing_episode_last() -> None:
    late = make_torrent("Example Show|1|9")
    early = make_torrent("Example Show|1|2")
    missing = make_torrent("Example Show|1|")
    client = MagicMock()
    client.search_multi.return_value = {"results": [{"id": 42, "media_type": "tv"}]}
    client.get_tv_details.return_value = {"id": 42, "name": "Example Show"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([late, missing, early], "api-key")

    assert response["groups"][0]["seasons"] == [
        {"season": 1, "episodes": [early, late, missing]}
    ]
    assert response["other"] == []


def test_title_lookup_deduplicates_case_insensitively() -> None:
    results = [make_torrent("Example Show|1|1"), make_torrent("example show|1|2")]
    client = MagicMock()
    client.search_multi.return_value = {"results": []}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        enrich_search_results(results, "api-key")

    client.search_multi.assert_called_once_with("Example Show")


def test_movie_years_stay_on_separate_cards() -> None:
    dune_2021 = make_torrent("Dune|||2021", seeds=20)
    dune_1984 = make_torrent("Dune|||1984", seeds=11)
    client = MagicMock()
    client.search_multi.return_value = {
        "results": [
            {"id": 438631, "media_type": "movie", "title": "Dune", "release_date": "2021-09-15"},
            {"id": 841, "media_type": "movie", "title": "Dune", "release_date": "1984-12-14"},
        ]
    }
    client.get_movie_details.side_effect = lambda tmdb_id: (
        {"id": 438631, "title": "Dune", "release_date": "2021-09-15"}
        if tmdb_id == 438631
        else {"id": 841, "title": "Dune", "release_date": "1984-12-14"}
    )

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([dune_2021, dune_1984], "api-key")

    by_year = {group["year"]: group["results"] for group in response["groups"]}
    assert by_year == {2021: [dune_2021], 1984: [dune_1984]}
    assert response["other"] == []


def test_movie_with_a_different_year_is_not_added_to_the_only_card() -> None:
    dune_2021 = make_torrent("Dune|||2021")
    dune_1984 = make_torrent("Dune|||1984")
    client = MagicMock()
    client.search_multi.return_value = {
        "results": [{"id": 438631, "media_type": "movie", "title": "Dune", "release_date": "2021-09-15"}]
    }
    client.get_movie_details.return_value = {"id": 438631, "title": "Dune", "release_date": "2021-09-15"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([dune_2021, dune_1984], "api-key")

    assert [group["year"] for group in response["groups"]] == [2021]
    assert response["groups"][0]["results"] == [dune_2021]
    assert response["other"] == [{**dune_1984, "parsed_title": "Dune"}]


def test_release_from_before_the_show_does_not_join_its_card() -> None:
    episode = make_torrent("Dune Prophecy|1|1|2024", seeds=8)
    older = make_torrent("Dune|1||2000", seeds=3)
    client = MagicMock()
    client.search_multi.side_effect = lambda query: (
        {"results": [{"id": 9, "media_type": "tv", "name": "Dune: Prophecy", "first_air_date": "2024-11-17"}]}
        if query == "Dune Prophecy"
        else {
            "results": [
                {"id": 9, "media_type": "tv", "name": "Dune: Prophecy", "first_air_date": "2024-11-17"},
                {"id": 100, "media_type": "movie", "title": "Dune", "release_date": "2021-09-15"},
            ]
        }
    )
    client.get_tv_details.return_value = {"id": 9, "name": "Dune: Prophecy", "first_air_date": "2024-11-17"}
    client.get_movie_details.return_value = {"id": 100, "title": "Dune", "release_date": "2021-09-15"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([episode, older], "api-key")

    prophecy = next(group for group in response["groups"] if group["title"] == "Dune: Prophecy")
    assert prophecy["seasons"][0]["episodes"] == [episode]
    assert response["other"] == [{**older, "parsed_title": "Dune"}]


def test_tv_episode_year_stays_on_the_series_card() -> None:
    episode = make_torrent("Example Show|1|1|2009")
    client = MagicMock()
    client.search_multi.return_value = {
        "results": [{"id": 42, "media_type": "tv", "name": "Example Show", "first_air_date": "2005-01-01"}]
    }
    client.get_tv_details.return_value = {"id": 42, "name": "Example Show", "first_air_date": "2005-01-01"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([episode], "api-key")

    assert response["groups"][0]["year"] == 2005
    assert response["groups"][0]["seasons"] == [{"season": 1, "episodes": [episode]}]
    assert response["other"] == []


def test_part_one_release_joins_the_movie_when_its_own_lookup_misses() -> None:
    dune = make_torrent("Dune|||2021", seeds=5)
    part_one = make_torrent("Dune Part One|||2021", seeds=6)
    client = MagicMock()
    client.search_multi.side_effect = lambda query: (
        {"results": [{"id": 100, "media_type": "movie", "title": "Dune", "release_date": "2021-09-15"}]}
        if query == "Dune"
        else {"results": []}
    )
    client.get_movie_details.return_value = {"id": 100, "title": "Dune", "release_date": "2021-09-15"}

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([dune, part_one], "api-key")

    assert response["groups"][0]["results"] == [dune, part_one]
    assert response["other"] == []


def test_one_word_season_pack_joins_the_show_and_not_the_movie() -> None:
    season_pack = make_torrent("MobLand S02 1080P AMZN WEB-DL DDP5.1. X265 POOTLED", seeds=13)
    dashed = make_torrent("Mobland - S01 - Mp4 x264 AC3 1080p", seeds=572)
    movie = make_torrent("Dune|||2021", seeds=4)
    dune_pack = make_torrent("Dune S01 COMPLETE 1080p", seeds=2)
    client = MagicMock()

    def search(query: str) -> dict[str, object]:
        if query == "MobLand":
            return {"results": [{"id": 247718, "media_type": "tv", "name": "MobLand", "first_air_date": "2025-03-30"}]}
        if query == "Dune":
            return {"results": [{"id": 438631, "media_type": "movie", "title": "Dune", "release_date": "2021-09-15"}]}
        return {"results": []}

    client.search_multi.side_effect = search
    client.get_tv_details.return_value = {"id": 247718, "name": "MobLand", "first_air_date": "2025-03-30"}
    client.get_movie_details.return_value = {"id": 438631, "title": "Dune", "release_date": "2021-09-15"}

    with patch("app.result_grouping.TMDBClient", return_value=client):
        response = enrich_search_results([season_pack, dashed, movie, dune_pack], "api-key")

    show = next(group for group in response["groups"] if group["title"] == "MobLand")
    by_season = {season["season"]: [item["title"] for item in season["episodes"]] for season in show["seasons"]}
    assert dashed["title"] in by_season[1]
    assert season_pack["title"] in by_season[2]
    film = next(group for group in response["groups"] if group["title"] == "Dune")
    assert film["results"] == [movie]
    assert response["other"] == [{**dune_pack, "parsed_title": "Dune"}]


def test_season_packs_join_each_covered_full_season() -> None:
    episode = make_torrent("Slow Horses S01E01 1080p WEB", seeds=4)
    single = make_torrent("Slow Horses - S04 - Mp4 x264 AC3 1080p", seeds=97)
    spanned = make_torrent(
        "Slow Horses 2022 Seasons 1 to 5 Complete 1080p WEB x264 [i_c]",
        seeds=56,
    )
    client = MagicMock()
    client.search_multi.return_value = {
        "results": [{"id": 95480, "media_type": "tv", "name": "Slow Horses", "first_air_date": "2022-04-01"}]
    }
    client.get_tv_details.return_value = {
        "id": 95480,
        "name": "Slow Horses",
        "first_air_date": "2022-04-01",
    }

    with patch("app.result_grouping.TMDBClient", return_value=client):
        response = enrich_search_results([episode, single, spanned], "api-key")

    group = response["groups"][0]
    by_season = {season["season"]: [item["title"] for item in season["episodes"]] for season in group["seasons"]}
    assert single["title"] in by_season[4]
    assert single["title"] not in by_season[1]
    for season_number in range(1, 6):
        assert spanned["title"] in by_season[season_number]
    assert spanned["title"] not in by_season.get(6, [])
    other_titles = [item["title"] for item in response["other"]]
    assert single["title"] not in other_titles
    assert spanned["title"] not in other_titles


def test_parser_exception_does_not_abort_or_drop_original_result() -> None:
    result = make_torrent("Malformed.Name.S01E02")
    client = MagicMock()
    client.search_multi.return_value = {"results": []}

    with (
        patch("app.result_grouping.parse_title", side_effect=ValueError("invalid title")),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results([result], "api-key")

    assert response["other"] == [{**result, "parsed_title": "Malformed Name S01E02"}]
    assert client.search_multi.call_args_list == [call("Malformed Name S01E02")]


def test_focus_fetches_only_the_chosen_show_and_drops_other_titles() -> None:
    friends = make_torrent("Friends|1|2", seeds=8)
    other = make_torrent("Friends with Benefits|", seeds=3)
    client = MagicMock()
    client.get_tv_details.return_value = {
        "id": 1668,
        "name": "Friends",
        "first_air_date": "1994-09-22",
        "poster_path": "/friends.jpg",
    }
    client.get_image_url.return_value = "https://image.tmdb.org/t/p/w185/friends.jpg"

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results(
            [friends, other],
            "api-key",
            ("tv", 1668),
            query_title="Friends",
        )

    client.search_multi.assert_not_called()
    client.get_movie_details.assert_not_called()
    client.get_tv_details.assert_called_once_with(1668)
    assert response["other"] == []
    assert len(response["groups"]) == 1
    group = response["groups"][0]
    assert group["tmdb_id"] == 1668
    assert group["media_type"] == "tv"
    titles = [item["title"] for season in group["seasons"] for item in season["episodes"]]
    assert titles == [friends["title"]]


def test_focus_movie_keeps_only_the_matching_year() -> None:
    current = make_torrent("Dune|||2021", seeds=4)
    older = make_torrent("Dune|||1984", seeds=2)
    client = MagicMock()
    client.get_movie_details.return_value = {
        "id": 438631,
        "title": "Dune",
        "release_date": "2021-09-15",
    }

    with (
        patch("app.result_grouping.parse_title", side_effect=lambda title: parsed_title(title)),
        patch("app.result_grouping.TMDBClient", return_value=client),
    ):
        response = enrich_search_results(
            [current, older],
            "api-key",
            ("movie", 438631),
            query_title="Dune",
        )

    client.search_multi.assert_not_called()
    client.get_tv_details.assert_not_called()
    client.get_movie_details.assert_called_once_with(438631)
    assert response["other"] == []
    assert [item["title"] for item in response["groups"][0]["results"]] == [current["title"]]


def test_season_episode_details_keeps_plot_still_and_rating() -> None:
    client = MagicMock()
    client.get_image_url.return_value = "https://image.tmdb.org/t/p/w300/still.jpg"
    payload = {
        "episodes": [
            {
                "episode_number": 2,
                "name": "Daddy Issues",
                "overview": "Lamb is on alert.",
                "air_date": "2026-09-23",
                "runtime": 47,
                "vote_average": 8.54,
                "vote_count": 12,
                "still_path": "/still.jpg",
            },
            {"episode_number": "nope"},
            "not-an-episode",
        ]
    }

    episodes = season_episode_details(client, payload)

    assert episodes == [
        {
            "episode_number": 2,
            "name": "Daddy Issues",
            "overview": "Lamb is on alert.",
            "air_date": "2026-09-23",
            "runtime": 47,
            "vote_average": 8.5,
            "still_url": "https://image.tmdb.org/t/p/w300/still.jpg",
        }
    ]
    client.get_image_url.assert_called_once_with("/still.jpg", size="w300")
    assert season_episode_details(client, None) == []
