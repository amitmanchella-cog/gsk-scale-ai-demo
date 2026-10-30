"""GET /reps/{rep_id}/hcps (S1, AC1): territory scoping, filters, search, sort order, as-of override."""

from datetime import date

import pytest

ISLA_XU_REASON = "Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)"
HCP_VIEW_FIELDS = {
    "hcp_id",
    "hcp_name",
    "specialty",
    "segment",
    "territory_id",
    "last_visit_date",
    "days_since_last_visit",
    "open_follow_ups",
    "score",
    "reason",
    "factors",
}


@pytest.fixture(scope="module")
def r001(client_module):
    r = client_module.get("/reps/R001/hcps")
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def client_module():
    from fastapi.testclient import TestClient
    from navigator_app.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_ac1_only_territory_hcps(r001):
    assert r001["rep"] == {"rep_id": "R001", "rep_name": "Dev Okafor", "territory_id": "T001"}
    assert r001["territory"] == {"territory_id": "T001", "territory_name": "South-01", "region": "South"}
    assert r001["as_of"] == "2025-09-29"
    assert r001["count"] == 64
    assert len(r001["hcps"]) == 64
    assert all(hcp["territory_id"] == "T001" for hcp in r001["hcps"])
    assert len({hcp["hcp_id"] for hcp in r001["hcps"]}) == 64
    assert all(set(hcp) == HCP_VIEW_FIELDS for hcp in r001["hcps"])
    assert sum(hcp["segment"] == "A" for hcp in r001["hcps"]) == 15
    assert not any(hcp["hcp_id"] in {"H00052", "H00002"} for hcp in r001["hcps"])

    isla = next(hcp for hcp in r001["hcps"] if hcp["hcp_id"] == "H00733")
    assert isla == {
        "hcp_id": "H00733",
        "hcp_name": "Dr Isla Xu",
        "specialty": "GP",
        "segment": "A",
        "territory_id": "T001",
        "last_visit_date": "2025-08-09",
        "days_since_last_visit": 51,
        "open_follow_ups": 1,
        "score": 100,
        "reason": ISLA_XU_REASON,
        "factors": [
            {"name": "segment", "points": 40, "detail": "Segment A"},
            {"name": "days_since_last_visit", "points": 40, "detail": "51 days since last visit (capped)"},
            {"name": "open_follow_up", "points": 20, "detail": "1 open follow-up"},
        ],
    }


def test_ac1_filters_and_search(client, r001):
    everyone = r001["hcps"]

    gp = client.get("/reps/R001/hcps", params={"specialty": "GP"}).json()
    assert gp["count"] == len(gp["hcps"]) == sum(hcp["specialty"] == "GP" for hcp in everyone) == 20
    assert all(hcp["specialty"] == "GP" for hcp in gp["hcps"])

    seg_a = client.get("/reps/R001/hcps", params={"segment": "A"}).json()
    assert seg_a["count"] == 15
    assert all(hcp["segment"] == "A" for hcp in seg_a["hcps"])
    assert client.get("/reps/R001/hcps", params={"segment": "D"}).status_code == 422

    never_visited = [hcp for hcp in everyone if hcp["days_since_last_visit"] is None]
    assert len(never_visited) == 4
    overdue = client.get("/reps/R001/hcps", params={"min_days_since_last_visit": 30}).json()
    expected = [hcp for hcp in everyone if hcp["days_since_last_visit"] is None or hcp["days_since_last_visit"] >= 30]
    assert overdue["count"] == len(expected) > len(never_visited)
    assert [hcp["hcp_id"] for hcp in overdue["hcps"]] == [hcp["hcp_id"] for hcp in expected]
    huge = client.get("/reps/R001/hcps", params={"min_days_since_last_visit": 10_000}).json()
    assert [hcp["hcp_id"] for hcp in huge["hcps"]] == [hcp["hcp_id"] for hcp in never_visited]

    xu = client.get("/reps/R001/hcps", params={"q": "XU"}).json()
    assert xu["count"] >= 1
    assert all("xu" in hcp["hcp_name"].lower() for hcp in xu["hcps"])
    assert xu["count"] == sum("xu" in hcp["hcp_name"].lower() for hcp in everyone)
    assert client.get("/reps/R001/hcps", params={"q": "no such name"}).json() == {
        **r001,
        "count": 0,
        "hcps": [],
    }

    combined = client.get(
        "/reps/R001/hcps", params={"segment": "A", "min_days_since_last_visit": 30, "q": "xu", "specialty": "GP"}
    ).json()
    assert combined["count"] == 1
    assert combined["hcps"][0]["hcp_id"] == "H00733"
    assert combined["hcps"][0]["reason"] == ISLA_XU_REASON

    assert (
        client.get("/reps/R001/hcps", params={"segment": "A", "specialty": "Cardiology", "q": "xu"}).json()["count"]
        == 0
    )


def test_unknown_rep_404(client):
    r = client.get("/reps/R999/hcps")
    assert r.status_code == 404
    assert r.json() == {"detail": "unknown rep 'R999'"}


def test_sort_order(client, r001):
    keys = [(-hcp["score"], hcp["hcp_name"]) for hcp in r001["hcps"]]
    assert keys == sorted(keys)
    assert r001["hcps"][0]["score"] == 100
    assert r001["hcps"][-1]["score"] == 0

    filtered = client.get("/reps/R001/hcps", params={"segment": "B"}).json()["hcps"]
    filtered_keys = [(-hcp["score"], hcp["hcp_name"]) for hcp in filtered]
    assert filtered_keys == sorted(filtered_keys)


def test_as_of_override(client):
    later = client.get("/reps/R001/hcps", params={"as_of": "2025-10-29", "q": "Isla Xu"}).json()
    assert later["as_of"] == "2025-10-29"
    isla = later["hcps"][0]
    assert isla["last_visit_date"] == "2025-08-09"
    assert isla["days_since_last_visit"] == (date(2025, 10, 29) - date(2025, 8, 9)).days == 81

    earlier = client.get("/reps/R001/hcps", params={"as_of": "2025-08-01", "q": "Isla Xu"}).json()["hcps"][0]
    assert earlier["last_visit_date"] is None or earlier["last_visit_date"] < "2025-08-09"

    assert client.get("/reps/R001/hcps", params={"as_of": "not-a-date"}).status_code == 422
