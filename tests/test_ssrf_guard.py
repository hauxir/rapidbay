"""Regression tests for the SSRF guard on /api/torrent_url_to_magnet/."""

import pytest
import settings

from app.app import _is_fetchable_url


@pytest.fixture
def indexers(monkeypatch):
    monkeypatch.setattr(settings, "JACKETT_HOST", "http://jackett:9117")
    monkeypatch.setattr(settings, "PROWLARR_HOST", None)


def test_public_http_urls_are_allowed(indexers):
    assert _is_fetchable_url("http://example.com/a.torrent")
    assert _is_fetchable_url("https://example.com/a.torrent")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8899/probe",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/admin",
        "http://192.168.1.1/",
        "http://[::1]/",
        "http://localhost/",
    ],
)
def test_local_network_targets_are_rejected(indexers, url):
    assert not _is_fetchable_url(url)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://x/", "not a url", ""])
def test_non_http_schemes_are_rejected(indexers, url):
    assert not _is_fetchable_url(url)


def test_configured_indexer_is_exempt(indexers):
    # Jackett/Prowlarr normally live on a private docker network.
    assert _is_fetchable_url("http://jackett:9117/dl/abc")
    assert not _is_fetchable_url("http://prowlarr:9696/dl/abc")
