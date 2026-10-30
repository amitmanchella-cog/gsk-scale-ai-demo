"""``app.server`` (S5.1): API mounted under /api, root /health, SPA static files with index.html fallback."""

import pytest
from fastapi.testclient import TestClient
from navigator_app.server import DEFAULT_STATIC_DIR, create_app, resolve_static_dir


@pytest.fixture
def spa_dir(tmp_path):
    (tmp_path / "index.html").write_text('<!doctype html><html><body><div id="root"></div></body></html>')
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index-abc123.js").write_text("console.log('navigator')")
    return tmp_path


@pytest.fixture
def spa_client(spa_dir):
    with TestClient(create_app(static_dir=spa_dir)) as client:
        yield client


@pytest.fixture
def api_only_client(tmp_path):
    with TestClient(create_app(static_dir=tmp_path / "missing")) as client:
        yield client


def test_api_is_mounted_under_api_prefix(spa_client):
    r = spa_client.get("/api/reps")
    assert r.status_code == 200
    assert r.json()[0]["rep_id"] == "R001"
    assert spa_client.get("/api/reps/R001/hcps").json()["territory"]["territory_id"] == "T001"
    assert spa_client.get("/api/docs").status_code == 200
    assert spa_client.get("/api/openapi.json").status_code == 200


def test_root_health_matches_api_health(spa_client):
    root = spa_client.get("/health")
    assert root.status_code == 200
    assert root.json() == spa_client.get("/api/health").json()
    assert root.json()["status"] == "ok"
    assert root.json()["row_counts"]["reps"] == 30


def test_root_serves_index_html(spa_client):
    r = spa_client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert '<div id="root">' in r.text


def test_static_assets_are_served(spa_client):
    r = spa_client.get("/assets/index-abc123.js")
    assert r.status_code == 200
    assert "navigator" in r.text


def test_unknown_path_falls_back_to_index_html(spa_client):
    r = spa_client.get("/reps/R001/plan")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert '<div id="root">' in r.text


def test_missing_static_dir_points_at_docs(api_only_client):
    r = api_only_client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/api/docs"
    assert api_only_client.get("/health").status_code == 200
    assert api_only_client.get("/api/reps").status_code == 200


def test_resolve_static_dir(spa_dir, tmp_path, monkeypatch):
    assert resolve_static_dir(spa_dir) == spa_dir
    assert resolve_static_dir(tmp_path / "nope") is None
    monkeypatch.setenv("NAVIGATOR_STATIC_DIR", str(spa_dir))
    assert resolve_static_dir() == spa_dir
    monkeypatch.delenv("NAVIGATOR_STATIC_DIR")
    assert resolve_static_dir() in (DEFAULT_STATIC_DIR, None)
