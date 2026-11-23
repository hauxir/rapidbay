"""Path-to-URL mapping in the web seed reverse proxy."""

import pytest
import web_seed_proxy


@pytest.fixture(autouse=True)
def clean_registry():
    web_seed_proxy._registry.clear()
    yield
    web_seed_proxy._registry.clear()


def test_lookup_by_file_path():
    web_seed_proxy.register("torbox", "abc", "Show S01/Show S01E01.mp4", "https://a")
    assert web_seed_proxy._lookup("torbox", "abc", "Show%20S01/Show%20S01E01.mp4") == (
        "Show S01/Show S01E01.mp4",
        "https://a",
    )


def test_lone_file_torrent_is_requested_by_torrent_name():
    # libtorrent asks for <base>/<torrent name> when a torrent holds one file,
    # even when that file sits in a directory.
    web_seed_proxy.register(
        "torbox", "abc", "Show S01/Show S01E01.mp4", "https://a", aliases=["Show S01"]
    )
    assert web_seed_proxy._lookup("torbox", "abc", "Show%20S01") == (
        "Show S01/Show S01E01.mp4",
        "https://a",
    )


def test_refreshing_a_url_updates_its_aliases():
    web_seed_proxy.register(
        "torbox", "abc", "Show S01/Show S01E01.mp4", "https://old", aliases=["Show S01"]
    )
    web_seed_proxy.register("torbox", "abc", "Show S01/Show S01E01.mp4", "https://new")
    assert web_seed_proxy._lookup("torbox", "abc", "Show%20S01")[1] == "https://new"
    assert web_seed_proxy._lookup("torbox", "abc", "Show%20S01E01.mp4")[1] == "https://new"


def test_providers_are_kept_apart():
    web_seed_proxy.register("torbox", "abc", "a.mp4", "https://tb")
    assert web_seed_proxy._lookup("real_debrid", "abc", "a.mp4") is None
