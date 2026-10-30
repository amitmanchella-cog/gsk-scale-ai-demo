"""GET /scoring/rules and GET /scoring/explain."""

import json

from navigator_app.deps import set_rules
from navigator_app.scoring import DEFAULT_RULES, load_rules


def test_scoring_rules_defaults(client):
    r = client.get("/scoring/rules")
    assert r.status_code == 200
    assert r.json() == DEFAULT_RULES.to_dict()


def test_explain_ac2(client):
    r = client.get("/scoring/explain", params={"segment": "A", "days_since_last_visit": 45, "open_follow_ups": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 100
    assert body["reason"] == "Segment A (+40), 45 days since last visit (+40, capped), 1 open follow-up (+20)"
    assert [factor["name"] for factor in body["factors"]] == ["segment", "days_since_last_visit", "open_follow_up"]
    assert set(body["factors"][0]) == {"name", "points", "detail"}


def test_explain_ac3(client):
    r = client.get("/scoring/explain", params={"segment": "B", "days_since_last_visit": 3, "open_follow_ups": 0})
    assert r.status_code == 200
    assert r.json() == {
        "score": 0,
        "reason": "Visited 3 days ago (within 7 days)",
        "factors": [{"name": "recent_visit", "points": 0, "detail": "Visited 3 days ago (within 7 days)"}],
    }


def test_explain_never_visited_when_days_omitted(client):
    r = client.get("/scoring/explain", params={"segment": "B"})
    assert r.status_code == 200
    assert r.json()["score"] == 65
    assert r.json()["reason"] == "Segment B (+25), never visited (+40, capped)"


def test_explain_invalid_inputs(client):
    assert client.get("/scoring/explain", params={"segment": "Z", "days_since_last_visit": 10}).status_code == 422
    assert client.get("/scoring/explain", params={"days_since_last_visit": 10}).status_code == 422
    assert client.get("/scoring/explain", params={"segment": "A", "days_since_last_visit": -1}).status_code == 422
    assert client.get("/scoring/explain", params={"segment": "A", "open_follow_ups": "x"}).status_code == 422


def test_rules_from_env_are_in_effect(monkeypatch):
    from fastapi.testclient import TestClient
    from navigator_app.main import app

    monkeypatch.setenv("NAVIGATOR_SCORING_RULES", json.dumps({"segment_weights": {"A": 50, "B": 25, "C": 10}}))
    try:
        with TestClient(app) as client:
            assert client.get("/scoring/rules").json()["segment_weights"]["A"] == 50
            r = client.get("/scoring/explain", params={"segment": "A", "days_since_last_visit": 10})
            assert r.json()["score"] == 60
            assert r.json()["reason"] == "Segment A (+50), 10 days since last visit (+10)"
    finally:
        set_rules(None)
    monkeypatch.delenv("NAVIGATOR_SCORING_RULES")
    assert load_rules() == DEFAULT_RULES
