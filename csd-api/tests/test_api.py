from __future__ import annotations

from csd_core.reference.asthma import ACTIVITY_IDS, SCHEDULE, VISIT_IDS
from fastapi.testclient import TestClient

from csd_api.app import create_app

MOVE = {"type": "MoveVisit", "visit_id": "V-W12", "day": 99}


def test_health_and_the_seeded_reference_study(client: TestClient, root_id: str) -> None:
    assert client.get("/health").json() == {"status": "ok", "studies": 1}
    [study] = client.get("/studies").json()
    assert study["id"] == "asthma-ref"
    assert study["root_version_id"] == study["head_version_id"] == root_id
    assert study["version_count"] == 1
    assert "asthma" in study["title"]


def test_version_carries_the_graph_and_findings(client: TestClient, root_id: str) -> None:
    version = client.get(f"/versions/{root_id}").json()
    assert version["parent_id"] is None
    assert version["operation"] is None
    assert version["findings"] == []
    assert len(version["graph"]["plan"]["visits"]) == 7
    assert len(version["graph"]["plan"]["activities"]) == 8
    assert len(version["graph"]["intent"]["arms"]) == 2
    assert len(version["graph"]["intent"]["endpoints"]) == 3


def test_schedule_grid_matches_the_reference_matrix(client: TestClient, root_id: str) -> None:
    grid = client.get(f"/versions/{root_id}/schedule").json()
    assert [v["id"] for v in grid["visits"]] == list(VISIT_IDS)
    assert [v["day"] for v in grid["visits"]] == [-14, 1, 29, 85, 169, 365, 393]
    assert [r["activity_id"] for r in grid["rows"]] == list(ACTIVITY_IDS)
    for row in grid["rows"]:
        assert row["cells"] == [v in SCHEDULE[row["activity_id"]] for v in VISIT_IDS]


def test_at_least_ten_operation_types_are_exposed(client: TestClient) -> None:
    types = client.get("/operation-types").json()
    assert len(types) >= 10
    assert {"MoveVisit", "ChangeEndpointTiming", "ChangePrimaryEndpoint", "AddArm"} <= set(types)


def test_an_inapplicable_operation_is_422_and_creates_no_version(
    client: TestClient, root_id: str
) -> None:
    for operation in (
        {"type": "MoveVisit", "visit_id": "V-NOPE", "day": 99},
        {"type": "MoveVisit", "visit_id": "V-W12", "day": 29},  # Week 4 is already on Day 29
        {"type": "ChangeEndpointTiming", "endpoint_id": "EP-FEV1", "week": 12},
    ):
        response = client.post(f"/versions/{root_id}/operations", json=operation)
        assert response.status_code == 422, operation
        assert isinstance(response.json()["detail"], str)
    assert client.post(f"/versions/{root_id}/operations", json={"type": "Nope"}).status_code == 422
    assert len(client.get("/studies/asthma-ref/versions").json()) == 1


def test_only_a_branch_head_accepts_operations(client: TestClient, root_id: str) -> None:
    assert client.post(f"/versions/{root_id}/operations", json=MOVE).status_code == 201
    stale = client.post(
        f"/versions/{root_id}/operations", json={"type": "RemoveVisit", "visit_id": "V-W4"}
    )
    assert stale.status_code == 409
    assert "not the head" in stale.json()["detail"]


def test_unknown_ids_are_404(client: TestClient) -> None:
    for path in (
        "/versions/v-nope",
        "/versions/v-nope/findings",
        "/versions/v-nope/schedule",
        "/studies/nope",
        "/studies/nope/versions",
        "/studies/nope/branches",
    ):
        assert client.get(path).status_code == 404, path
    assert client.post("/versions/v-nope/operations", json=MOVE).status_code == 404


def test_new_studies_are_independent_sandboxes(client: TestClient, root_id: str) -> None:
    created = client.post("/studies", json={"id": "sandbox-1"})
    assert created.status_code == 201
    sandbox = created.json()
    assert sandbox["id"] == "sandbox-1"
    assert sandbox["root_version_id"] != root_id

    client.post(f"/versions/{sandbox['root_version_id']}/operations", json=MOVE)
    assert len(client.get("/studies/sandbox-1/versions").json()) == 2
    assert len(client.get("/studies/asthma-ref/versions").json()) == 1

    assert client.post("/studies", json={"id": "sandbox-1"}).status_code == 409
    assert client.post("/studies", json={"id": "Not Valid"}).status_code == 422
    generated = client.post("/studies").json()
    assert generated["id"].startswith("study-")
    assert [s["id"] for s in client.get("/studies").json()] == [
        "asthma-ref",
        "sandbox-1",
        generated["id"],
    ]


def test_branches_lists_main(client: TestClient, root_id: str) -> None:
    v1 = client.post(f"/versions/{root_id}/operations", json=MOVE).json()
    assert client.get("/studies/asthma-ref/branches").json() == [
        {
            "study_id": "asthma-ref",
            "name": "main",
            "base_version_id": None,
            "head_version_id": v1["id"],
        }
    ]


def test_versions_survive_a_restart(client: TestClient, root_id: str, database_url: str) -> None:
    v1 = client.post(f"/versions/{root_id}/operations", json=MOVE).json()

    with TestClient(create_app(database_url)) as restarted:
        assert restarted.get("/health").json()["studies"] == 1
        assert restarted.get(f"/versions/{v1['id']}").json() == v1
        assert restarted.get("/studies/asthma-ref").json()["head_version_id"] == v1["id"]


def test_openapi_documents_the_operation_union(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/versions/{version_id}/operations" in schema["paths"]
    assert "MoveVisit" in schema["components"]["schemas"]
