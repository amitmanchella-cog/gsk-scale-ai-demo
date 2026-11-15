from __future__ import annotations

import json
from pathlib import Path

import pytest

from pda_api.documents import UnsupportedDocumentError, read_document
from pda_api.evaluation import field_f1
from pda_api.providers import get_provider
from pda_api.providers.mock import MockProvider, parse_age, split_sections
from pda_api.schemas import ProtocolDesign
from tests.conftest import as_docx, sample_text

LABELLED = Path(__file__).parent / "fixtures" / "labelled" / "eligibility.json"


def test_extraction_field_f1_on_labelled_set(provider: MockProvider) -> None:
    labelled = json.loads(LABELLED.read_text())
    assert len(labelled) == 10
    metrics = field_f1(provider, labelled)
    assert metrics["f1"] >= 0.85, metrics


def test_field_f1_penalises_wrong_expectations(provider: MockProvider) -> None:
    wrong = [{"text": "Inclusion Criteria:\n- Aged 18 to 65 years", "expected": {"min_age": 30, "n_inclusion": 4}}]
    assert field_f1(provider, wrong)["f1"] < 0.5


def test_weak_sample_design(weak_design: ProtocolDesign) -> None:
    assert weak_design.indication == "type_2_diabetes"
    assert (weak_design.phase, weak_design.phase_group) == ("PHASE3", 3)
    assert weak_design.target_enrollment == 900
    assert weak_design.site_count == 8
    assert [(c.country, c.sites) for c in weak_design.planned_countries] == [("United States", 5), ("China", 3)]
    assert (weak_design.population.min_age, weak_design.population.max_age) == (40, 60)
    assert weak_design.population.summary and "Middle-aged adults" in weak_design.population.summary
    assert [c.id for c in weak_design.criteria] == [f"I{i}" for i in range(1, 10)] + [f"E{i}" for i in range(1, 16)]
    by_id = {c.id: c for c in weak_design.criteria}
    assert (by_id["I3"].parameter, by_id["I3"].lower, by_id["I3"].upper) == ("hba1c", 7.5, 8.5)
    assert (by_id["I4"].parameter, by_id["I4"].lower, by_id["I4"].upper) == ("bmi", 27, 32)
    assert (by_id["I6"].parameter, by_id["I6"].lower, by_id["I6"].upper) == ("egfr", 90, None)
    assert by_id["E14"].category == "other_trial"
    assert weak_design.warnings == []
    # Text after the criteria (treatment, statistics) must not leak into the last criterion.
    assert "SYN-4471" not in by_id["E15"].text


@pytest.mark.parametrize(
    ("key", "indication", "phase_group", "enrollment", "sites", "countries"),
    [("asthma_phase3", "asthma", 3, 640, 95, 6), ("copd_phase2", "copd", 2, 320, 48, 4)],
)
def test_other_samples(
    provider: MockProvider, key: str, indication: str, phase_group: int, enrollment: int, sites: int, countries: int
) -> None:
    design = provider.extract_design(sample_text(key))
    assert (design.indication, design.phase_group) == (indication, phase_group)
    assert (design.target_enrollment, design.site_count) == (enrollment, sites)
    assert len(design.planned_countries) == countries
    assert sum(c.sites or 0 for c in design.planned_countries) == sites


def test_free_form_wording(provider: MockProvider) -> None:
    text = (
        "A phase II study of drug X in COPD\n"
        "We plan to enrol 150 patients at 12 centres in the UK.\n"
        "Inclusion criteria:\n- Aged 40 years or older\nExclusion criteria:\n- Asthma\n"
    )
    design = provider.extract_design(text)
    assert (design.indication, design.phase, design.target_enrollment, design.site_count) == ("copd", "PHASE2", 150, 12)
    assert [(c.country, c.sites) for c in design.planned_countries] == [("United Kingdom", 12)]
    assert design.population.min_age == 40


def test_unrecognised_document_reports_warnings(provider: MockProvider) -> None:
    design = provider.extract_design("Minutes of a meeting about nothing in particular.")
    assert design.indication is None and design.criteria == []
    assert "Could not extract indication." in design.warnings


@pytest.mark.parametrize(
    ("text", "exclusion", "expected"),
    [
        ("Aged 18 to 65 years", False, (18, 65)),
        ("Age ≥ 18 years", False, (18, None)),
        ("65 years of age or younger", False, (None, 65)),
        ("Age below 18 years", True, (18, None)),
        ("Age over 75 years", True, (None, 75)),
        ("History of malignancy within 5 years", False, (None, None)),
        ("Aged 70 to 60 years", False, (None, None)),
    ],
)
def test_parse_age(text: str, exclusion: bool, expected: tuple[float | None, float | None]) -> None:
    bounds = parse_age(text, exclusion=exclusion)
    assert (bounds.lower, bounds.upper) == expected


def test_split_sections_stops_at_next_heading() -> None:
    eligibility, rest = split_sections("Title: T\n4. INCLUSION CRITERIA\n1. Aged 18\n5. STUDY TREATMENT\nDrug\n")
    assert eligibility.splitlines() == ["Inclusion Criteria:", "1. Aged 18"]
    assert "Drug" in rest and "Aged 18" not in rest


def test_docx_and_text_give_the_same_design(provider: MockProvider) -> None:
    text = sample_text("copd_phase2")
    from_docx = provider.extract_design(read_document("copd.docx", as_docx(text)))
    assert from_docx == provider.extract_design(read_document("copd.txt", text.encode()))


def test_read_document_rejects_other_types() -> None:
    with pytest.raises(UnsupportedDocumentError):
        read_document("protocol.pdf", b"%PDF")
    with pytest.raises(UnsupportedDocumentError):
        read_document("broken.docx", b"not a zip")
    assert read_document("latin.txt", "café".encode("latin-1")) == "café"


def test_only_the_mock_provider_is_shipped() -> None:
    assert get_provider("mock").name == "mock"
    with pytest.raises(ValueError, match="Only 'mock' is shipped"):
        get_provider("openai")


def test_mock_provider_makes_no_network_calls(monkeypatch: pytest.MonkeyPatch, provider: MockProvider) -> None:
    import socket

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert provider.extract_design(sample_text("asthma_phase3")).indication == "asthma"
