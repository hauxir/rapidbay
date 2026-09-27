"""Route tests for the TMDB-enriched search endpoint."""

from collections.abc import Iterator
from unittest.mock import Mock
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import app as app_module


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create a client without entering the app lifespan (which starts the daemon)."""
    app_module.app.dependency_overrides[app_module.authorize] = Mock(return_value=None)
    try:
        yield TestClient(app_module.app)
    finally:
        app_module.app.dependency_overrides.clear()


def _episode(title: str, seeds: int = 5) -> dict[str, Any]:
    return {
        "title": title,
        "seeds": seeds,
        "magnet": "magnet:?xt=urn:btih:abc",
        "torrent_link": None,
        "status": "downloading",
    }


def _response(groups: list[dict[str, Any]] | None = None,
              other: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"groups": groups or [], "other": other or []}


def _configure_indexers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.settings, "JACKETT_HOST", "http://jackett")
    monkeypatch.setattr(app_module.settings, "PROWLARR_HOST", None)


def test_empty_search_calls_indexer_and_returns_empty_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_indexers(monkeypatch)
    indexer_search = Mock(return_value=[])
    status = Mock(side_effect=lambda results: results)
    monkeypatch.setattr(app_module, "_indexer_search", indexer_search)
    monkeypatch.setattr(app_module, "_add_status_to_results", status)
    monkeypatch.setattr(app_module, "enrich_search_results", lambda results, key: _response())

    response = client.get("/api/rich_search/")

    assert response.status_code == 200
    assert response.json() == _response()
    indexer_search.assert_called_once_with("")
    status.assert_called_once_with([])


def test_focused_title_is_forwarded_without_a_broad_lookup(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_indexers(monkeypatch)
    monkeypatch.setattr(app_module.settings, "TMDB_API_KEY", "tmdb-key")
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: [])
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda results: results)
    calls: list[tuple[Any, ...]] = []

    def enrich(results: list[dict[str, Any]], api_key: str | None, focus=None, query_title: str = "") -> dict[str, Any]:
        calls.append((results, api_key, focus, query_title))
        return _response()

    monkeypatch.setattr(app_module, "enrich_search_results", enrich)

    response = client.get("/api/rich_search/Friends?media=tv&tmdb=1668")

    assert response.status_code == 200
    assert calls == [([], "tmdb-key", ("tv", 1668), "Friends")]


def test_search_with_tmdb_key_passes_results_and_key_to_enricher(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_indexers(monkeypatch)
    monkeypatch.setattr(app_module.settings, "TMDB_API_KEY", "tmdb-key")
    raw_results = [_episode("The Matrix 1999")]
    status_results = [_episode("The Matrix 1999", seeds=9)]
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: raw_results)
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda results: status_results)
    calls: list[tuple[list[dict[str, Any]], str | None]] = []

    def enrich(results: list[dict[str, Any]], api_key: str | None) -> dict[str, Any]:
        calls.append((results, api_key))
        return _response(other=[{**results[0], "parsed_title": "The Matrix"}])

    monkeypatch.setattr(app_module, "enrich_search_results", enrich)

    response = client.get("/api/rich_search/The%20Matrix")

    assert response.status_code == 200
    assert calls == [(status_results, "tmdb-key")]
    assert response.json()["other"][0]["parsed_title"] == "The Matrix"


def test_search_without_tmdb_key_returns_parsed_other_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_indexers(monkeypatch)
    monkeypatch.setattr(app_module.settings, "TMDB_API_KEY", None)
    results = [_episode("Better.Call.Saul.S03E06")]
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: results)
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda items: items)
    monkeypatch.setattr(
        app_module,
        "enrich_search_results",
        lambda items, key: _response(other=[{**items[0], "parsed_title": "Better Call Saul"}]),
    )

    response = client.get("/api/rich_search/test")

    assert response.status_code == 200
    assert response.json()["groups"] == []
    assert response.json()["other"][0]["parsed_title"] == "Better Call Saul"


def test_search_with_no_indexer_returns_empty_without_searching(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module.settings, "JACKETT_HOST", None)
    monkeypatch.setattr(app_module.settings, "PROWLARR_HOST", None)
    monkeypatch.setattr(
        app_module,
        "_indexer_search",
        lambda term: pytest.fail("indexer should not be called when none is configured"),
    )
    monkeypatch.setattr(
        app_module,
        "_add_status_to_results",
        lambda results: pytest.fail("status should not be calculated without an indexer"),
    )

    response = client.get("/api/rich_search/test")

    assert response.status_code == 200
    assert response.json() == _response()


def test_search_can_return_only_other_results(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_indexers(monkeypatch)
    item = {**_episode("Unknown.Release.Name"), "parsed_title": "Unknown Release Name"}
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: [_episode("Unknown.Release.Name")])
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda results: results)
    monkeypatch.setattr(app_module, "enrich_search_results", lambda results, key: _response(other=[item]))

    response = client.get("/api/rich_search/unknown")

    assert response.status_code == 200
    assert response.json() == _response(other=[item])


def test_tv_group_response_uses_ordered_season_wire_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_indexers(monkeypatch)
    episode_one = _episode("Show S02E01")
    episode_two = _episode("Show S02E02")
    expected = _response(
        groups=[
            {
                "tmdb_id": 42,
                "title": "Show",
                "year": 2020,
                "poster_url": "https://image.tmdb.org/t/p/w185/poster.jpg",
                "media_type": "tv",
                "overview": None,
                "genres": [],
                "vote_average": None,
                "backdrop_url": None,
                "runtime": None,
                "latest_episode": None,
                "seasons": [{"season": 2, "episodes": [episode_one, episode_two]}],
                "results": [],
            }
        ]
    )
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: [episode_one, episode_two])
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda results: results)
    monkeypatch.setattr(app_module, "enrich_search_results", lambda results, key: expected)

    response = client.get("/api/rich_search/show")

    assert response.status_code == 200
    assert response.json() == expected
    assert isinstance(response.json()["groups"][0]["seasons"], list)


def test_movie_group_keeps_items_in_results_and_seasons_empty(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_indexers(monkeypatch)
    item = _episode("The Matrix 1999")
    expected = _response(
        groups=[
            {
                "tmdb_id": 603,
                "title": "The Matrix",
                "year": 1999,
                "poster_url": None,
                "media_type": "movie",
                "overview": None,
                "genres": [],
                "vote_average": None,
                "backdrop_url": None,
                "runtime": None,
                "latest_episode": None,
                "seasons": [],
                "results": [item],
            }
        ]
    )
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: [item])
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda results: results)
    monkeypatch.setattr(app_module, "enrich_search_results", lambda results, key: expected)

    response = client.get("/api/rich_search/matrix")

    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["groups"][0]["seasons"] == []
    assert len(response.json()["groups"][0]["results"]) == 1


def test_search_more_than_lookup_limit_enriches_all_results_but_tmdb_caps_lookups(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import result_grouping

    _configure_indexers(monkeypatch)
    monkeypatch.setattr(app_module.settings, "TMDB_API_KEY", "tmdb-key")
    results = [_episode(f"Title {index}") for index in range(35)]
    monkeypatch.setattr(app_module, "_indexer_search", lambda term: results)
    monkeypatch.setattr(app_module, "_add_status_to_results", lambda items: items)

    class FakeTMDBClient:
        def __init__(self, api_key: str) -> None:
            assert api_key == "tmdb-key"
            self.lookups: list[str] = []

        def search_multi(self, query: str) -> dict[str, Any]:
            self.lookups.append(query)
            return {"results": []}

    clients: list[FakeTMDBClient] = []

    def make_client(api_key: str) -> FakeTMDBClient:
        client_instance = FakeTMDBClient(api_key)
        clients.append(client_instance)
        return client_instance

    monkeypatch.setattr(result_grouping, "TMDBClient", make_client)

    response = client.get("/api/rich_search/many")

    assert response.status_code == 200
    assert len(response.json()["other"]) == 35
    assert len(clients) == 1
    assert len(clients[0].lookups) == result_grouping.MAX_TMDB_LOOKUPS == 30
