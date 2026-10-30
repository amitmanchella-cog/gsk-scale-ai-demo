from navigator_app import __version__
from navigator_app.data import TABLES


def test_health_reports_row_counts(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert set(body["row_counts"]) == set(TABLES)
    assert all(count > 0 for count in body["row_counts"].values())
    assert body["row_counts"]["reps"] == 30
    assert body["row_counts"]["territories"] == 20


def test_list_reps(client):
    r = client.get("/reps")
    assert r.status_code == 200
    reps = r.json()
    assert len(reps) == 30
    assert [rep["rep_id"] for rep in reps] == sorted(rep["rep_id"] for rep in reps)
    first = reps[0]
    assert set(first) == {"rep_id", "rep_name", "territory_id", "region", "hire_date"}
    assert first["rep_id"] == "R001"
    assert first["territory_id"] == "T001"
    assert first["region"] == "South"
    assert all(rep["region"] for rep in reps)


def test_list_territories(client):
    r = client.get("/territories")
    assert r.status_code == 200
    territories = r.json()
    assert len(territories) == 20
    assert territories[0] == {"territory_id": "T001", "territory_name": "South-01", "region": "South"}
    assert {t["region"] for t in territories} == {"Central", "East", "North", "South", "West"}


def test_cors_allows_vite_dev_server(client):
    r = client.options(
        "/reps",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_as_of_defaults_to_latest_visit(client):
    assert client.get("/health").json()["as_of"] == "2025-09-29"


def test_health_as_of_env_override(client, monkeypatch):
    monkeypatch.setenv("NAVIGATOR_AS_OF_DATE", "2025-08-01")
    assert client.get("/health").json()["as_of"] == "2025-08-01"
