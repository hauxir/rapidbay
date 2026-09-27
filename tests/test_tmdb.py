"""Tests for the TMDB v3 client."""

from unittest.mock import MagicMock, call, patch

import requests

from app.tmdb import TMDBClient


def make_response(status_code: int = 200, payload: object = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_search_multi_returns_json_dict_on_success() -> None:
    payload = {"results": [{"id": 1, "media_type": "tv"}]}
    with patch("app.tmdb.requests.get", return_value=make_response(payload=payload)) as get:
        client = TMDBClient(api_key="test")

        result = client.search_multi("Breaking Bad")

    assert result == payload
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/search/multi",
        params={"api_key": "test", "query": "Breaking Bad"},
        timeout=30,
    )


def test_search_multi_sends_v4_read_token_as_bearer() -> None:
    token = "header.payload.signature"
    payload = {"results": [{"id": 1, "media_type": "movie"}]}
    with patch("app.tmdb.requests.get", return_value=make_response(payload=payload)) as get:
        result = TMDBClient(api_key=token).search_multi("Dune")

    assert result == payload
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/search/multi",
        params={"query": "Dune"},
        timeout=30,
        headers={"Authorization": "Bearer header.payload.signature"},
    )


def test_get_tv_details_returns_json_dict_on_success() -> None:
    payload = {"id": 1396, "name": "Breaking Bad"}
    with patch("app.tmdb.requests.get", return_value=make_response(payload=payload)) as get:
        result = TMDBClient(api_key="test").get_tv_details(1396)

    assert result == payload
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/tv/1396", params={"api_key": "test"}, timeout=30
    )


def test_get_tv_season_requests_the_season_endpoint() -> None:
    payload = {"id": 1, "episodes": [{"episode_number": 1, "name": "Pilot"}]}
    with patch("app.tmdb.requests.get", return_value=make_response(payload=payload)) as get:
        result = TMDBClient(api_key="test").get_tv_season(1396, 1)

    assert result == payload
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/tv/1396/season/1", params={"api_key": "test"}, timeout=30
    )


def test_get_movie_details_returns_json_dict_on_success() -> None:
    payload = {"id": 603, "title": "The Matrix"}
    with patch("app.tmdb.requests.get", return_value=make_response(payload=payload)) as get:
        result = TMDBClient(api_key="test").get_movie_details(603)

    assert result == payload
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/movie/603", params={"api_key": "test"}, timeout=30
    )


def test_get_image_url_with_valid_path() -> None:
    assert TMDBClient(api_key="test").get_image_url("/abc.jpg") == "https://image.tmdb.org/t/p/w185/abc.jpg"


def test_get_image_url_with_none_path() -> None:
    assert TMDBClient(api_key="test").get_image_url(None) is None


def test_get_image_url_with_custom_size() -> None:
    assert TMDBClient(api_key="test").get_image_url("/abc.jpg", "original") == (
        "https://image.tmdb.org/t/p/original/abc.jpg"
    )


def test_search_multi_network_timeout_returns_none() -> None:
    with patch("app.tmdb.requests.get", side_effect=requests.Timeout):
        assert TMDBClient(api_key="test").search_multi("query") is None


def test_search_multi_connection_error_returns_none() -> None:
    with patch("app.tmdb.requests.get", side_effect=requests.ConnectionError):
        assert TMDBClient(api_key="test").search_multi("query") is None


def test_search_multi_http_404_returns_none() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(status_code=404)):
        assert TMDBClient(api_key="test").search_multi("query") is None


def test_search_multi_http_500_returns_none() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(status_code=500)):
        assert TMDBClient(api_key="test").search_multi("query") is None


def test_search_multi_non_json_response_returns_none() -> None:
    response = make_response()
    response.json.side_effect = ValueError("invalid JSON")
    with patch("app.tmdb.requests.get", return_value=response):
        assert TMDBClient(api_key="test").search_multi("query") is None


def test_search_multi_preserves_empty_results() -> None:
    payload = {"results": []}
    with patch("app.tmdb.requests.get", return_value=make_response(payload=payload)):
        assert TMDBClient(api_key="test").search_multi("no matches") == payload


def test_search_multi_encodes_special_query_as_param() -> None:
    query = "Amélie & Friends/Part 2"
    with patch("app.tmdb.requests.get", return_value=make_response(payload={"results": []})) as get:
        TMDBClient(api_key="test").search_multi(query)

    get.assert_called_once_with(
        "https://api.themoviedb.org/3/search/multi",
        params={"api_key": "test", "query": query},
        timeout=30,
    )


def test_get_tv_details_nonexistent_id_returns_none() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(status_code=404)):
        assert TMDBClient(api_key="test").get_tv_details(999999999) is None


def test_get_movie_details_nonexistent_id_returns_none() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(status_code=404)):
        assert TMDBClient(api_key="test").get_movie_details(999999999) is None


def test_search_multi_unexpected_non_dict_shape_returns_none() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(payload=[{"id": 1}])):
        assert TMDBClient(api_key="test").search_multi("query") is None


def test_init_stores_api_key() -> None:
    assert TMDBClient(api_key="test-key").api_key == "test-key"


def test_get_image_url_with_empty_string_path() -> None:
    assert TMDBClient(api_key="test").get_image_url("") is None


def test_search_multi_with_empty_query() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(payload={"results": []})) as get:
        TMDBClient(api_key="test").search_multi("")

    get.assert_called_once_with(
        "https://api.themoviedb.org/3/search/multi",
        params={"api_key": "test", "query": ""},
        timeout=30,
    )


def test_get_tv_details_with_zero_id() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(payload={"id": 0})) as get:
        result = TMDBClient(api_key="test").get_tv_details(0)

    assert result == {"id": 0}
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/tv/0", params={"api_key": "test"}, timeout=30
    )


def test_get_movie_details_with_zero_id() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(payload={"id": 0})) as get:
        result = TMDBClient(api_key="test").get_movie_details(0)

    assert result == {"id": 0}
    get.assert_called_once_with(
        "https://api.themoviedb.org/3/movie/0", params={"api_key": "test"}, timeout=30
    )


def test_multiple_searches_use_same_client() -> None:
    first = make_response(payload={"results": [{"id": 1}]})
    second = make_response(payload={"results": [{"id": 2}]})
    with patch("app.tmdb.requests.get", side_effect=[first, second]) as get:
        client = TMDBClient(api_key="test")
        first_result = client.search_multi("first")
        second_result = client.search_multi("second")

    assert first_result == {"results": [{"id": 1}]}
    assert second_result == {"results": [{"id": 2}]}
    assert get.call_args_list == [
        call(
            "https://api.themoviedb.org/3/search/multi",
            params={"api_key": "test", "query": "first"},
            timeout=30,
        ),
        call(
            "https://api.themoviedb.org/3/search/multi",
            params={"api_key": "test", "query": "second"},
            timeout=30,
        ),
    ]


def test_two_clients_keep_different_keys_independent() -> None:
    with patch("app.tmdb.requests.get", return_value=make_response(payload={"results": []})) as get:
        first_client = TMDBClient(api_key="first-key")
        second_client = TMDBClient(api_key="second-key")
        first_client.search_multi("first")
        second_client.search_multi("second")

    assert get.call_args_list == [
        call(
            "https://api.themoviedb.org/3/search/multi",
            params={"api_key": "first-key", "query": "first"},
            timeout=30,
        ),
        call(
            "https://api.themoviedb.org/3/search/multi",
            params={"api_key": "second-key", "query": "second"},
            timeout=30,
        ),
    ]
