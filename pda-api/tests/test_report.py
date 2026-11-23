from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from pda_api.report import Grid, Text, blocks, num, pct, render_html
from pda_api.schemas import Report
from tests.conftest import WEAK, sample_text, upload
from tests.test_privacy import person_values


def _report(client: TestClient, protocol_id: str, **params: object) -> Report:
    response = client.get(f"/api/protocols/{protocol_id}/report", params={"format": "json", **params})
    assert response.status_code == 200, response.text
    return Report.model_validate(response.json())


def _pdf_text(content: bytes) -> str:
    # Table cells wrap, so compare with all whitespace removed.
    return "".join("".join(page.extract_text() for page in PdfReader(BytesIO(content)).pages).split())


@pytest.fixture()
def protocol_id(client: TestClient) -> str:
    return upload(client)


@pytest.fixture()
def accepted(client: TestClient, protocol_id: str) -> list[str]:
    suggestions = client.get(f"/api/protocols/{protocol_id}/suggestions").json()["suggestions"]
    return [suggestions[0]["id"], suggestions[2]["id"]]


def test_report_values_equal_the_other_endpoints(client: TestClient, protocol_id: str, accepted: list[str]) -> None:
    report = _report(client, protocol_id, accept=accepted)
    base = f"/api/protocols/{protocol_id}"
    suggestions = {item["id"]: item for item in client.get(f"{base}/suggestions").json()["suggestions"]}
    changes = [suggestions[identifier]["change"] for identifier in accepted]
    what_if = client.post(f"{base}/what-if", json={"changes": changes}).json()

    assert report.design.model_dump(mode="json") == client.get(base).json()["design"]
    assert report.assessment.model_dump(mode="json") == client.get(f"{base}/assessment").json()
    assert report.baseline.model_dump(mode="json") == client.get(f"{base}/forecast").json()
    assert report.scenario is not None
    assert report.scenario.model_dump(mode="json") == what_if["scenario"]
    assert [change.model_dump(mode="json") for change in report.accepted_changes] == [
        suggestions[identifier] for identifier in accepted
    ]
    assert report.scenario.p50_months < report.baseline.p50_months


def test_report_lists_every_cited_trial(client: TestClient, protocol_id: str, accepted: list[str]) -> None:
    report = _report(client, protocol_id, accept=accepted)
    expected = {nct_id for change in report.accepted_changes for nct_id in change.cited_trial_ids}
    expected |= set(report.baseline.termination_risk.trial_ids)
    expected |= {trial.nct_id for score in report.assessment.criteria for trial in score.driving_trials}

    assert all(len(change.cited_trial_ids) >= 5 for change in report.accepted_changes)
    assert {trial.nct_id for trial in report.cited_trials} == expected
    assert all(trial.cited_for for trial in report.cited_trials)


@pytest.mark.parametrize("fmt", ["html", "pdf"])
def test_both_formats_contain_the_same_content(
    client: TestClient, protocol_id: str, accepted: list[str], fmt: str
) -> None:
    report = _report(client, protocol_id, accept=accepted)
    response = client.get(f"/api/protocols/{protocol_id}/report", params={"format": fmt, "accept": accepted})
    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith(f'.{fmt}"')
    if fmt == "pdf":
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")
        text = _pdf_text(response.content)
    else:
        assert response.headers["content-type"].startswith("text/html")
        text = "".join(response.text.split())

    def present(value: str) -> bool:
        return "".join(value.split()) in text

    scenario = report.scenario
    assert scenario is not None
    for value in (
        num(report.baseline.p50_months),
        num(report.baseline.p90_months),
        num(scenario.p50_months),
        num(scenario.p90_months),
        pct(report.baseline.termination_risk.risk),
        "Withacceptedchanges",
    ):
        assert present(value), value
    for change in report.accepted_changes:
        assert present(change.title), change.title
    for score in report.assessment.criteria:
        assert present(f"{score.criterion_id}"), score.criterion_id
    for trial in report.cited_trials:
        assert present(trial.nct_id), trial.nct_id


def test_html_is_self_contained_and_escapes_text(client: TestClient, protocol_id: str) -> None:
    report = _report(client, protocol_id)
    report.design.title = "<script>alert(1)</script>"
    html = render_html(report)

    assert "<script" not in html
    assert "&lt;script&gt;" in html
    assert "<link" not in html and "src=" not in html
    assert html.startswith("<!doctype html>")


def test_draft_only_report_does_not_build_suggestions(
    client: TestClient, protocol_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(context: object) -> None:
        raise AssertionError("suggest() was called for a report without accepted changes")

    monkeypatch.setattr("pda_api.report.suggest", fail)
    assert _report(client, protocol_id).accepted_changes == []


def test_report_without_accepted_changes(client: TestClient, protocol_id: str) -> None:
    report = _report(client, protocol_id)
    assert report.scenario is None
    assert report.accepted_changes == []
    html = client.get(f"/api/protocols/{protocol_id}/report").text
    assert "No changes were accepted." in html
    assert "With accepted changes" not in html


def test_every_table_row_matches_its_header(client: TestClient, protocol_id: str, accepted: list[str]) -> None:
    grids = [block for block in blocks(_report(client, protocol_id, accept=accepted)) if isinstance(block, Grid)]
    assert len(grids) == 4
    for grid in grids:
        assert grid.rows
        assert all(len(row) == len(grid.headers) for row in grid.rows)


def test_unknown_suggestion_is_rejected(client: TestClient, protocol_id: str) -> None:
    response = client.get(f"/api/protocols/{protocol_id}/report", params={"accept": "S99"})
    assert response.status_code == 422
    assert "S99" in response.json()["detail"]


def test_unknown_protocol_and_format(client: TestClient, protocol_id: str) -> None:
    assert client.get("/api/protocols/missing/report").status_code == 404
    assert client.get(f"/api/protocols/{protocol_id}/report", params={"format": "docx"}).status_code == 422


def test_report_contains_no_person_level_data(client: TestClient, protocol_id: str, accepted: list[str]) -> None:
    html = client.get(f"/api/protocols/{protocol_id}/report", params={"accept": accepted}).text
    assert person_values(html) == []


def _upload_with_criterion(client: TestClient, criterion: str) -> str:
    text = sample_text(WEAK)
    original = "4. BMI between 27 and 32 kg/m2."
    assert original in text
    response = client.post(
        "/api/protocols",
        files={"file": ("draft.txt", text.replace(original, f"4. {criterion}"), "text/plain")},
    )
    assert response.status_code == 201, response.text
    protocol_id: str = response.json()["id"]
    return protocol_id


def test_pdf_keeps_the_direction_of_comparison_operators(client: TestClient) -> None:
    protocol_id = _upload_with_criterion(client, "Fasting C-peptide ≥ 0.8 ng/mL and eGFR ≤ 90 at screening.")
    response = client.get(f"/api/protocols/{protocol_id}/report", params={"format": "pdf"})
    assert response.status_code == 200, response.text
    assert "FastingC-peptide>=0.8ng/mLandeGFR<=90atscreening." in _pdf_text(response.content)


def test_pdf_splits_a_row_taller_than_a_page(client: TestClient) -> None:
    sentence = "Participants must have documented stable disease on two visits. "
    protocol_id = _upload_with_criterion(client, (sentence * 400).strip())
    response = client.get(f"/api/protocols/{protocol_id}/report", params={"format": "pdf"})
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")
    # The repeated table header lands inside a sentence at each page break, so count one word.
    assert _pdf_text(response.content).count("documented") == 400


def test_forecast_text_names_the_percentile_fallback(client: TestClient, protocol_id: str) -> None:
    report = _report(client, protocol_id)
    fallback = report.baseline.model_copy(update={"rate_source": "indication_phase_benchmark", "n_rates": 0})
    texts = [
        block.text for block in blocks(report.model_copy(update={"baseline": fallback})) if isinstance(block, Text)
    ]
    assert any("drawn from the indication and phase percentiles" in text for text in texts)
    assert not any("0 benchmark rates" in text for text in texts)


def test_report_shows_the_population_summary(client: TestClient, protocol_id: str) -> None:
    report = _report(client, protocol_id)
    summary = report.design.population.summary
    assert summary
    html = client.get(f"/api/protocols/{protocol_id}/report").text
    assert f"<td>Population</td><td>{summary}</td>" in html


def test_json_upload_time_is_utc_like_the_protocol_response(client: TestClient, protocol_id: str) -> None:
    created_at = client.get(f"/api/protocols/{protocol_id}/report", params={"format": "json"}).json()["created_at"]
    assert created_at.endswith(("Z", "+00:00"))
    assert created_at == client.get(f"/api/protocols/{protocol_id}").json()["created_at"]


@pytest.mark.parametrize("fmt", ["html", "pdf"])
def test_report_is_built_and_rendered_off_the_event_loop(
    client: TestClient, protocol_id: str, monkeypatch: pytest.MonkeyPatch, fmt: str
) -> None:
    import pda_api.routers.report as router

    on_loop: dict[str, bool] = {}

    def record(name: str) -> None:
        original = getattr(router, name)

        def wrapper(*args: object) -> object:
            try:
                asyncio.get_running_loop()
                on_loop[name] = True
            except RuntimeError:
                on_loop[name] = False
            return original(*args)

        monkeypatch.setattr(router, name, wrapper)

    record("build_report")
    record(f"render_{fmt}")
    assert client.get(f"/api/protocols/{protocol_id}/report", params={"format": fmt}).status_code == 200
    assert on_loop == {"build_report": False, f"render_{fmt}": False}


@pytest.mark.parametrize("fmt", ["html", "pdf"])
def test_export_does_not_contain_the_full_protocol_id(client: TestClient, protocol_id: str, fmt: str) -> None:
    response = client.get(f"/api/protocols/{protocol_id}/report", params={"format": fmt})
    text = _pdf_text(response.content) if fmt == "pdf" else response.text
    assert f"Reportreference:{protocol_id[:8]}." in "".join(text.split())
    assert protocol_id not in text
    assert protocol_id.encode() not in response.content
