"""Route tests for the classic frontend, and for calling the API from another origin."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app as app_module


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    classic = tmp_path / "classic"
    classic.mkdir()
    (classic / "index.html").write_text("classic index")
    (classic / "login.html").write_text("classic login")
    (classic / "app.js").write_text("classic js")
    monkeypatch.setattr(app_module.settings, "FRONTEND_DIR", str(classic))
    monkeypatch.setattr(app_module.settings, "PASSWORD", None)
    return TestClient(app_module.app)


def test_classic_frontend_is_served_at_root(client: TestClient) -> None:
    assert client.get("/").text == "classic index"
    assert client.get("/search/foo").text == "classic index"
    assert client.get("/app.js").text == "classic js"


def test_rich_paths_fall_through_to_the_classic_frontend(client: TestClient) -> None:
    assert client.get("/rich/").text == "classic index"
    response = client.get("/rich", follow_redirects=False)
    assert response.status_code == 200
    assert response.text == "classic index"


def test_wrong_password_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.settings, "PASSWORD", "secret")
    assert client.post("/api", data={"password": "nope"}).status_code == 401


def test_correct_password_sets_the_cookie(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.settings, "PASSWORD", "secret")
    response = client.post("/api", data={"password": "secret"})
    assert response.status_code == 200
    assert response.json() == {}
    assert "password=secret" in response.headers["set-cookie"]


def test_bearer_token_authorizes_api_calls(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.settings, "PASSWORD", "secret")
    denied = client.get("/api/home/")
    assert denied.status_code == 404
    allowed = client.get("/api/home/", headers={"Authorization": "Bearer secret"})
    assert allowed.status_code == 200


def test_preflight_without_origin_header_is_allowed(client: TestClient) -> None:
    """Cloudflare quick tunnels strip Origin on OPTIONS before it reaches the app."""
    response = client.options(
        "/api/library/observe/",
        headers={
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_preflight_allows_authorization_header(client: TestClient) -> None:
    response = client.options(
        "/api/home/",
        headers={
            "Origin": "https://rich.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers
