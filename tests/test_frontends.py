"""Route tests for serving the classic frontend at / and the rich frontend at /rich/."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app as app_module


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    classic = tmp_path / "classic"
    rich = tmp_path / "rich"
    classic.mkdir()
    rich.mkdir()
    (classic / "index.html").write_text("classic index")
    (classic / "login.html").write_text("classic login")
    (classic / "app.js").write_text("classic js")
    (rich / "index.html").write_text("rich index")
    (rich / "app.js").write_text("rich js")
    monkeypatch.setattr(app_module.settings, "FRONTEND_DIR", str(classic))
    monkeypatch.setattr(app_module.settings, "RICH_FRONTEND_DIR", str(rich))
    monkeypatch.setattr(app_module.settings, "PASSWORD", None)
    return TestClient(app_module.app)


def test_classic_frontend_is_served_at_root(client: TestClient) -> None:
    assert client.get("/").text == "classic index"
    assert client.get("/search/foo").text == "classic index"
    assert client.get("/app.js").text == "classic js"


def test_rich_frontend_is_served_under_rich(client: TestClient) -> None:
    assert client.get("/rich/").text == "rich index"
    assert client.get("/rich/search/foo").text == "rich index"
    assert client.get("/rich/app.js").text == "rich js"


def test_rich_without_trailing_slash_redirects(client: TestClient) -> None:
    response = client.get("/rich", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/rich/"


def test_rich_frontend_uses_classic_login(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.settings, "PASSWORD", "secret")
    assert client.get("/rich/").text == "classic login"
    client.cookies.set("password", "secret")
    assert client.get("/rich/").text == "rich index"
