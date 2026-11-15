from __future__ import annotations

import pytest

from pda_data.criteria import (
    Bounds,
    classify_why_stopped,
    item_categories,
    item_thresholds,
    parse_age_years,
    parse_bounds,
    parse_eligibility,
    split_criteria,
)

ELIGIBILITY = """Inclusion Criteria:

* Adults aged 18 to 75 years
* HbA1c between 7.0% and 10.5% at screening
  confirmed by the central laboratory
* BMI ≤ 40 kg/m2

Exclusion Criteria:

* eGFR \\< 45 mL/min/1.73m2
* Pregnant or breastfeeding women
"""


def test_split_criteria_sections_and_continuations() -> None:
    inclusion, exclusion = split_criteria(ELIGIBILITY)
    assert len(inclusion) == 3
    assert len(exclusion) == 2
    assert inclusion[1].endswith("confirmed by the central laboratory")


def test_split_criteria_handles_inline_headers_and_empty_text() -> None:
    inclusion, exclusion = split_criteria("Inclusion criteria: adults with asthma\nExclusion criteria: smokers")
    assert inclusion == ["adults with asthma"]
    assert exclusion == ["smokers"]
    assert split_criteria(None) == ([], [])


def test_parse_eligibility_thresholds_and_categories() -> None:
    parsed = parse_eligibility(ELIGIBILITY)
    assert parsed.thresholds["hba1c"] == Bounds(7.0, 10.5)
    assert parsed.thresholds["bmi"] == Bounds(None, 40.0)
    # an exclusion of eGFR < 45 means the allowed window starts at 45
    assert parsed.thresholds["egfr"] == Bounds(45.0, None)
    assert {"hba1c", "bmi", "renal", "pregnancy"} <= set(parsed.categories)


@pytest.mark.parametrize(
    ("text", "exclusion", "expected"),
    [
        ("fev1 >= 40% and <= 80% of predicted", False, Bounds(40.0, 80.0)),
        ("fev1 of 30-80 % predicted", False, Bounds(30.0, 80.0)),
        ("hba1c > 11%", True, Bounds(None, 11.0)),
        ("hba1c < 6.5%", True, Bounds(6.5, None)),
        ("hba1c at screening", False, Bounds()),
        ("hba1c >= 250", False, Bounds()),
    ],
)
def test_parse_bounds(text: str, exclusion: bool, expected: Bounds) -> None:
    low, high = (10.0, 130.0) if text.startswith("fev1") else (4.0, 15.0)
    assert parse_bounds(text, low, high, exclusion=exclusion) == expected


def test_item_thresholds_reads_verbal_operators() -> None:
    assert item_thresholds("Smoking history of at least 10 pack-years", exclusion=False) == {
        "pack_years": Bounds(10.0, None)
    }
    assert item_thresholds("Body mass index greater than 45 kg/m2", exclusion=True) == {"bmi": Bounds(None, 45.0)}


def test_item_categories() -> None:
    assert item_categories("History of myocardial infarction or stroke") == ["cardiovascular"]
    assert item_categories("Able to walk") == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [("18 Years", 18.0), ("6 Months", 0.5), ("N/A", None), (None, None), ("12 Weeks", 0.23)],
)
def test_parse_age_years(value: str | None, expected: float | None) -> None:
    assert parse_age_years(value) == expected


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("Slow recruitment", "low_accrual"),
        ("Due to slow accrual, study team has decided to end the study early.", "low_accrual"),
        ("Unable to enroll", "low_accrual"),
        ("Terminated due to adverse events", "safety"),
        ("Company decision: No Safety or Efficacy Concerns", "efficacy_futility"),
        ("Sponsor decision not related to safety reasons", "business"),
        ("Futility at interim analysis", "efficacy_futility"),
        ("End of funding", "funding"),
        ("COVID-19 pandemic", "other"),
        ("", "none"),
        (None, "none"),
    ],
)
def test_classify_why_stopped(reason: str | None, expected: str) -> None:
    assert classify_why_stopped(reason) == expected
