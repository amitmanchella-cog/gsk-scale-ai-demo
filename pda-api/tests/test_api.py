from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import WEAK, as_docx, sample_text, upload


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["llm_provider"] == "mock" and body["benchmark_trials"] > 2000


def test_upload_text_returns_design_and_can_be_fetched(client: TestClient) -> None:
    response = client.post("/api/protocols", files={"file": ("weak.txt", sample_text(WEAK), "text/plain")})
    assert response.status_code == 201
    body = response.json()
    assert body["document"] == "weak.txt"
    assert body["design"]["indication"] == "type_2_diabetes"
    assert len(body["design"]["criteria"]) == 24
    assert all(criterion["text"] for criterion in body["design"]["criteria"])
    assert client.get(f"/api/protocols/{body['id']}").json() == body


def test_upload_docx(client: TestClient) -> None:
    files = {"file": ("copd.docx", as_docx(sample_text("copd_phase2")), "application/octet-stream")}
    body = client.post("/api/protocols", files=files).json()
    assert body["design"]["indication"] == "copd"
    assert body["design"]["site_count"] == 48


def test_upload_errors(client: TestClient) -> None:
    assert client.post("/api/protocols", files={"file": ("p.pdf", b"%PDF", "application/pdf")}).status_code == 415
    unknown = client.post("/api/protocols", files={"file": ("p.txt", b"nothing useful", "text/plain")})
    assert unknown.status_code == 422
    assert "Could not extract indication." in unknown.json()["detail"]["warnings"]
    big = client.post("/api/protocols", files={"file": ("p.txt", b"x" * 2_000_001, "text/plain")})
    assert big.status_code == 413
    assert client.get("/api/protocols/does-not-exist").status_code == 404
    assert client.get("/api/protocols/does-not-exist/assessment").status_code == 404


def test_upload_strips_directories_from_the_document_label(client: TestClient) -> None:
    files = {"file": ("../../etc/weak.txt", sample_text(WEAK), "text/plain")}
    assert client.post("/api/protocols", files=files).json()["document"] == "weak.txt"


def test_assessment(client: TestClient) -> None:
    protocol_id = upload(client)
    body = client.get(f"/api/protocols/{protocol_id}/assessment").json()
    assert 20 <= len(body["similar_trials"]) <= 50
    assert body["summary"]["n_similar"] == len(body["similar_trials"])
    assert len(body["criteria"]) == 24
    assert body["red_flags"] == sum(1 for c in body["criteria"] if c["level"] == "high") >= 4
    assert 0 <= body["overall_score"] <= 100
    assert len(client.get(f"/api/protocols/{protocol_id}/assessment?similar=25").json()["similar_trials"]) == 25
    assert client.get(f"/api/protocols/{protocol_id}/assessment?similar=5").status_code == 422


def test_assessment_is_deterministic(client: TestClient) -> None:
    protocol_id = upload(client)
    url = f"/api/protocols/{protocol_id}/assessment"
    assert client.get(url).json() == client.get(url).json()


def test_competing_trials(client: TestClient) -> None:
    protocol_id = upload(client)
    body = client.get(f"/api/protocols/{protocol_id}/competing-trials").json()
    assert body["indication"] == "type_2_diabetes"
    assert [c["country"] for c in body["countries"]] == ["United States", "China"]
    assert all(c["competing_trials"] > 0 for c in body["countries"])


def test_samples(client: TestClient) -> None:
    samples = client.get("/api/samples").json()
    assert {s["key"] for s in samples} == {"asthma_phase3", "copd_phase2", "t2d_phase3_weak"}
    assert [s["key"] for s in samples if s["weak"]] == [WEAK]
    assert {s["indication"] for s in samples} == {"asthma", "copd", "type_2_diabetes"}
    assert client.get(f"/api/samples/{WEAK}").text == sample_text(WEAK)
    assert client.get("/api/samples/nope").status_code == 404
    assert client.get("/api/samples/..%2F..%2Fpyproject").status_code == 404
