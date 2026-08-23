"""Regression tests for the SSRF guard on /api/torrent_url_to_magnet/.

DNS is stubbed so these stay hermetic - the point is the policy and the
connection pinning, not name resolution.
"""

import contextlib
import http.server
import ipaddress
import socket
import threading

import pytest
import settings

from app.app import _fetch_target_ip, _get_pinned

FAKE_DNS = {
    "jackett": "172.18.0.5",
    "tracker.test": "93.184.216.34",
    "loopback.test": "127.0.0.1",
    "metadata.test": "169.254.169.254",
    "multicast.test": "224.0.0.1",
    "lan.test": "192.168.1.7",
    "v6loopback.test": "::1",
}


@pytest.fixture(autouse=True)
def stub_dns_and_indexers(monkeypatch):
    monkeypatch.setattr(settings, "JACKETT_HOST", "http://jackett:9117")
    monkeypatch.setattr(settings, "PROWLARR_HOST", None)

    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host not in FAKE_DNS:
            with contextlib.suppress(ValueError):
                # IP literals still resolve for real, so a pinned connection
                # can actually be made.
                ipaddress.ip_address(host)
                return real_getaddrinfo(host, port, *args, **kwargs)
            raise socket.gaierror(f"stubbed NXDOMAIN for {host}")
        ip = FAKE_DNS[host]
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def test_public_host_is_allowed_and_pinned():
    assert _fetch_target_ip("http://tracker.test/a.torrent") == "93.184.216.34"
    assert _fetch_target_ip("https://tracker.test/a.torrent") == "93.184.216.34"


@pytest.mark.parametrize(
    "url",
    [
        "http://loopback.test/probe",
        "http://metadata.test/latest/meta-data/",
        "http://multicast.test/x",
        "http://lan.test/admin",
        "http://v6loopback.test/x",
    ],
)
def test_local_network_targets_are_rejected(url):
    assert _fetch_target_ip(url) is None


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "gopher://tracker.test/", "not a url", "", "http://nxdomain.test/x"]
)
def test_non_http_and_unresolvable_are_rejected(url):
    assert _fetch_target_ip(url) is None


def test_indexer_exemption_is_scoped_to_its_origin():
    # Jackett/Prowlarr normally live on a private docker network, so the
    # configured origin is exempt - but only that exact origin.
    assert _fetch_target_ip("http://jackett:9117/dl/abc") == "172.18.0.5"
    assert _fetch_target_ip("http://jackett:22/x") is None
    assert _fetch_target_ip("https://jackett:9117/x") is None
    assert _fetch_target_ip("http://prowlarr:9696/x") is None


def test_connection_is_pinned_and_keeps_the_real_host_header():
    """Closes the DNS-rebinding window: the socket goes to the validated IP,
    not to whatever the name resolves to at connect time."""
    seen = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen["host"] = self.headers.get("Host")
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # "unresolvable.test" is absent from FAKE_DNS, so this can only
        # connect at all because the address is pinned.
        response = _get_pinned(f"http://unresolvable.test:{port}/dl/x", "127.0.0.1", timeout=10)
        assert response.status_code == 200
        assert seen["host"] == f"unresolvable.test:{port}"
    finally:
        server.shutdown()
        server.server_close()
