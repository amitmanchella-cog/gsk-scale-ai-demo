"""M11 drafts over HTTP."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _root(client: TestClient) -> str:
    return str(client.get("/studies").json()[0]["root_version_id"])


def _element_ids(client: TestClient, version_id: str) -> set[str]:
    graph = client.get(f"/versions/{version_id}").json()["graph"]
    intent, plan = graph["intent"], graph["plan"]
    nodes = [
        *intent["objectives"],
        *intent["estimands"],
        *intent["endpoints"],
        *intent["design_activities"],
        *intent["arms"],
        *plan["visits"],
        *plan["activities"],
        *plan["standards"],
    ]
    cells = {f"{c['visit_id']}:{c['activity_id']}" for c in plan["schedule"]}
    return {n["id"] for n in nodes} | cells


def test_drafts_return_sections_3_5_and_8_from_the_template_provider(client: TestClient) -> None:
    response = client.get(f"/versions/{_root(client)}/drafts")

    assert response.status_code == 200
    draft = response.json()
    assert draft["provider"] == "template"
    assert [(s["number"], s["title"]) for s in draft["sections"]] == [
        ("3", "Trial Objectives and Associated Estimands"),
        ("5", "Trial Design"),
        ("8", "Trial Assessments and Procedures"),
    ]


def test_every_sentence_has_an_element_id_that_exists_in_that_version(client: TestClient) -> None:
    root = _root(client)
    moved = client.post(
        f"/versions/{root}/operations", json={"type": "RemoveVisit", "visit_id": "V-W4"}
    ).json()["id"]

    for version_id in (root, moved):
        known = _element_ids(client, version_id)
        sections = client.get(f"/versions/{version_id}/drafts").json()["sections"]
        sentences = [s for section in sections for s in section["sentences"]]
        assert len(sentences) > 20
        for sentence in sentences:
            assert sentence["element_ids"], sentence["text"]
            assert set(sentence["element_ids"]) <= known, sentence["text"]


def test_a_single_section_follows_the_version(client: TestClient) -> None:
    root = _root(client)
    moved = client.post(
        f"/versions/{root}/operations", json={"type": "MoveVisit", "visit_id": "V-W12", "day": 99}
    ).json()["id"]

    before = client.get(f"/versions/{root}/drafts/8").json()
    after = client.get(f"/versions/{moved}/drafts/8").json()

    assert before["number"] == after["number"] == "8"
    week12 = next(s for s in after["sentences"] if s["text"].startswith("Week 12 "))
    assert "on Day 99" in week12["text"]
    assert week12["element_ids"][0] == "V-W12"
    assert any("Week 12 takes place on site on Day 85" in s["text"] for s in before["sentences"])


@pytest.mark.parametrize("path", ["/versions/v-missing/drafts", "/versions/v-missing/drafts/8"])
def test_drafts_of_an_unknown_version_are_not_found(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


def test_an_unknown_section_is_rejected(client: TestClient) -> None:
    assert client.get(f"/versions/{_root(client)}/drafts/4").status_code == 422
