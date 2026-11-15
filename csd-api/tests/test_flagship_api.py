"""The flagship scenario over HTTP, version by version (see the comment on MBA-3867)."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

MOVE = {"type": "MoveVisit", "visit_id": "V-W12", "day": 99}
RETIME = {"type": "ChangeEndpointTiming", "endpoint_id": "EP-FEV1", "week": 14}


def test_flagship_scenario_reproduces_exactly(client: TestClient, root_id: str) -> None:
    assert client.get(f"/versions/{root_id}/findings").json()["count"] == 0

    moved = client.post(f"/versions/{root_id}/operations", json=MOVE)
    assert moved.status_code == 201
    v1 = moved.json()
    assert v1["parent_id"] == root_id
    assert v1["seq"] == 1
    assert v1["operation"] == MOVE

    findings = client.get(f"/versions/{v1['id']}/findings").json()
    assert findings["count"] == 1
    [finding] = findings["findings"]
    assert finding["id"] == "unmet_endpoint_timepoint:EP-FEV1"
    assert finding["type"] == "unmet_endpoint_timepoint"
    assert finding["severity"] == "warning"
    assert finding["subject_id"] == "EP-FEV1"
    assert finding["element_ids"] == ["EP-FEV1", "DA-SPIRO"]
    assert finding["message"] == (
        'Primary endpoint "Change from baseline in trough FEV1" is timed at Week 12 (Day 85), '
        "but no visit performs Spirometry within its window of that day. "
        'The nearest is "Week 12" on Day 99 (window of 3 days).'
    )

    retimed = client.post(f"/versions/{v1['id']}/operations", json=RETIME)
    assert retimed.status_code == 201
    v2 = retimed.json()
    assert v2["parent_id"] == v1["id"]
    assert v2["findings"] == []
    assert client.get(f"/versions/{v2['id']}/findings").json() == {
        "version_id": v2["id"],
        "count": 0,
        "findings": [],
    }
    [fev1] = [e for e in v2["graph"]["intent"]["endpoints"] if e["id"] == "EP-FEV1"]
    assert fev1["timepoint"] == {"week": 14}

    # Each step is its own version; the earlier ones are unchanged.
    timeline = client.get("/studies/asthma-ref/versions").json()
    assert [(v["id"], v["seq"], v["finding_count"]) for v in timeline] == [
        (root_id, 0, 0),
        (v1["id"], 1, 1),
        (v2["id"], 2, 0),
    ]
    assert client.get(f"/versions/{root_id}").json()["findings"] == []
    assert client.get(f"/versions/{v1['id']}").json()["findings"] == [finding]
    assert client.get("/studies/asthma-ref").json()["head_version_id"] == v2["id"]


def test_each_operation_is_checked_in_under_one_second(client: TestClient, root_id: str) -> None:
    head = root_id
    for operation in (MOVE, RETIME, {"type": "RemoveVisit", "visit_id": "V-W4"}):
        start = time.perf_counter()
        response = client.post(f"/versions/{head}/operations", json=operation)
        elapsed = time.perf_counter() - start
        assert response.status_code == 201
        assert elapsed < 1.0
        head = response.json()["id"]
