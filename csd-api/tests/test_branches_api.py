"""Branches, scores and compare over HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from csd_api.app import create_app

REMOVE_W4 = {"type": "RemoveVisit", "visit_id": "V-W4"}
ACQ5_PRIMARY = {"type": "ChangePrimaryEndpoint", "endpoint_id": "EP-ACQ5"}
REFERENCE_SCORE = {"visit_count": 7, "patient_time_minutes": 640, "cost_proxy": 2160.0}
FEWER_SCORE = {"visit_count": 6, "patient_time_minutes": 550, "cost_proxy": 1940.0}


def branch(client: TestClient, version_id: str, name: str, operation: dict[str, object]) -> str:
    created = client.post(f"/versions/{version_id}/branches", json={"name": name})
    assert created.status_code == 201, created.text
    applied = client.post(
        f"/versions/{version_id}/operations", params={"branch": name}, json=operation
    )
    assert applied.status_code == 201, applied.text
    assert applied.json()["branch"] == name
    return str(applied.json()["id"])


def test_score_of_the_reference_study(client: TestClient, root_id: str) -> None:
    assert client.get(f"/versions/{root_id}/score").json() == REFERENCE_SCORE
    assert client.get("/versions/v-missing/score").status_code == 404


def test_create_a_branch_from_any_version(client: TestClient, root_id: str) -> None:
    v1 = client.post(
        f"/versions/{root_id}/operations",
        json={"type": "MoveVisit", "visit_id": "V-W12", "day": 99},
    ).json()
    # The root is no longer the head of main, but it can still be branched from.
    created = client.post(f"/versions/{root_id}/branches", json={"name": "fewer-visits"})
    assert created.status_code == 201
    assert created.json() == {
        "study_id": "asthma-ref",
        "name": "fewer-visits",
        "base_version_id": root_id,
        "head_version_id": root_id,
    }
    assert len(client.get("/studies/asthma-ref/versions").json()) == 2

    fewer = client.post(
        f"/versions/{root_id}/operations", params={"branch": "fewer-visits"}, json=REMOVE_W4
    ).json()
    assert (fewer["branch"], fewer["parent_id"], fewer["findings"]) == ("fewer-visits", root_id, [])
    heads = {
        b["name"]: b["head_version_id"] for b in client.get("/studies/asthma-ref/branches").json()
    }
    assert heads == {"main": v1["id"], "fewer-visits": fewer["id"]}
    # Main is untouched.
    assert client.get(f"/versions/{v1['id']}").json() == v1


def test_branch_errors(client: TestClient, root_id: str) -> None:
    assert client.post("/versions/v-missing/branches", json={"name": "x"}).status_code == 404
    assert client.post(f"/versions/{root_id}/branches", json={"name": "main"}).status_code == 422
    assert client.post(f"/versions/{root_id}/branches", json={"name": "Not OK"}).status_code == 422
    assert client.post(f"/versions/{root_id}/branches", json={}).status_code == 422
    unknown = client.post(
        f"/versions/{root_id}/operations", params={"branch": "missing"}, json=REMOVE_W4
    )
    assert unknown.status_code == 404
    branch(client, root_id, "alt", REMOVE_W4)
    stale = client.post(
        f"/versions/{root_id}/operations", params={"branch": "alt"}, json=ACQ5_PRIMARY
    )
    assert stale.status_code == 409
    assert len(client.get("/studies/asthma-ref/versions").json()) == 2


def test_fewer_visits_branch_scores_lower_than_main(client: TestClient, root_id: str) -> None:
    fewer = branch(client, root_id, "fewer-visits", REMOVE_W4)
    main = client.get(f"/versions/{root_id}/score").json()
    lighter = client.get(f"/versions/{fewer}/score").json()
    assert lighter == FEWER_SCORE
    assert all(lighter[key] < main[key] for key in REFERENCE_SCORE)


def test_compare_two_branches_side_by_side(client: TestClient, root_id: str) -> None:
    fewer = branch(client, root_id, "fewer-visits", REMOVE_W4)
    acq5 = branch(client, root_id, "acq5-primary", ACQ5_PRIMARY)
    response = client.get("/compare", params={"left": fewer, "right": acq5})
    assert response.status_code == 200
    body = response.json()
    assert body["left"] == {
        "version_id": fewer,
        "branch": "fewer-visits",
        "seq": 1,
        "score": FEWER_SCORE,
        "findings": [],
    }
    assert body["right"]["branch"] == "acq5-primary"
    assert body["right"]["score"] == REFERENCE_SCORE
    assert body["delta"] == {"visit_count": 1, "patient_time_minutes": 90, "cost_proxy": 220.0}
    changes = {(c["element_id"], c["change"]) for c in body["changes"]}
    assert ("V-W4", "added") in changes
    assert {("EP-FEV1", "changed"), ("EP-ACQ5", "changed")} <= changes
    assert len(changes) == 8


def test_compare_errors(client: TestClient, root_id: str) -> None:
    assert client.get("/compare", params={"left": root_id, "right": "v-missing"}).status_code == 404
    assert client.get("/compare", params={"left": root_id}).status_code == 422
    other = client.post("/studies", json={"id": "other"}).json()
    across = client.get("/compare", params={"left": root_id, "right": other["root_version_id"]})
    assert across.status_code == 422


def test_branches_survive_a_restart(client: TestClient, root_id: str, database_url: str) -> None:
    fewer = branch(client, root_id, "fewer-visits", REMOVE_W4)
    with TestClient(create_app(database_url)) as restarted:
        names = [b["name"] for b in restarted.get("/studies/asthma-ref/branches").json()]
        assert names == ["main", "fewer-visits"]
        assert restarted.get(f"/versions/{fewer}/score").json() == FEWER_SCORE
