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


def test_exclusion_header_in_the_middle_of_a_line_switches_section() -> None:
    # Shape of NCT03061214: the whole block is one line.
    text = (
        "Inclusion Criteria: - Male or female, age equal to or above 18 years "
        "Exclusion Criteria: - Impaired renal function defined as eGFR below 60 ml/min/1.73 m\\^2"
    )
    inclusion, exclusion = split_criteria(text)
    assert len(inclusion) == 1
    assert exclusion == ["Impaired renal function defined as eGFR below 60 ml/min/1.73 m\\^2"]
    assert parse_eligibility(text).thresholds["egfr"] == Bounds(60.0, None)


def test_key_header_is_not_split_after_key() -> None:
    inclusion, exclusion = split_criteria(
        "Key Inclusion Criteria: adults with COPD Key Exclusion Criteria: current asthma"
    )
    assert inclusion == ["adults with COPD"]
    assert exclusion == ["current asthma"]
    inclusion, _ = split_criteria("Key Inclusion Criteria:\n* Adults with COPD\n* Smokers")
    assert len(inclusion) == 2


def test_prose_mentioning_exclusion_criteria_does_not_switch_section() -> None:
    inclusion, exclusion = split_criteria(
        "Inclusion Criteria:\n* Meets none of the exclusion criteria: confirmed at screening"
    )
    assert len(inclusion) == 1
    assert exclusion == []


def test_escaped_and_lettered_numbering_starts_a_new_item() -> None:
    # Shape of NCT04609904.
    text = (
        "Inclusion Criteria:\n\n1\\. Adults with asthma\n\nExclusion Criteria:\n\n"
        "1\\. Respiratory infection within 4 weeks of V1.\n\n"
        "2a. Biological therapy for asthma would be appropriate.\n\n"
        "2b. Any investigational biologic within 4 months.\n\n"
        "3\\) Current smokers"
    )
    inclusion, exclusion = split_criteria(text)
    assert len(inclusion) == 1
    assert len(exclusion) == 4


def test_later_criteria_tighten_the_window() -> None:
    # Shape of NCT06739044: screening and randomisation limits on the same measure.
    parsed = parse_eligibility(
        "Inclusion Criteria:\n"
        "1. HbA1c 7.5 - 11.0 % (both inclusive) (screening)\n"
        "2. HbA1c 7.0 - 10.5 % (both inclusive) (randomisation)\n"
    )
    assert parsed.thresholds["hba1c"] == Bounds(7.5, 10.5)


def test_contradicting_window_is_ignored() -> None:
    parsed = parse_eligibility("Inclusion Criteria:\n* BMI 20-25 kg/m2\n* BMI 30-40 kg/m2 in cohort B\n")
    assert parsed.thresholds["bmi"] == Bounds(20.0, 25.0)


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
        ("fev1 within 20 to 60 minutes following up to 4 inhalations", False, Bounds()),
        ("fev1 >= 12% and >= 200 ml within 15-30 min", False, Bounds(12.0, None)),
        ("fev1 >= 60% within 30 days", False, Bounds(60.0, None)),
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


@pytest.mark.parametrize(
    "unit",
    ["mL/min/1.73m2", "milliliters per minute per 1.73 m2", "milliliter (mL)/minute (min)/1.73 m2", "ml.min-1.1.73 m2"],
)
def test_rate_units_still_give_a_renal_threshold(unit: str) -> None:
    assert item_thresholds(f"eGFR < 45 {unit}", exclusion=True) == {"egfr": Bounds(45.0, None)}


def test_item_thresholds_reads_value_first_comparisons() -> None:
    assert item_thresholds("7.5% ≤ HbA1c ≤ 11%", exclusion=False) == {"hba1c": Bounds(7.5, 11.0)}
    assert item_thresholds("18.5 < BMI < 35 kg/m2", exclusion=False) == {"bmi": Bounds(18.5, 35.0)}
    assert item_thresholds("10% < HbA1c", exclusion=True) == {"hba1c": Bounds(None, 10.0)}


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
        ("Study closed to accrual early due to side effects of study drug.", "safety"),
        ("Terminated after the recruitment had been completed due to a decision to discontinue development", "other"),
        ("Closed to accrual because of slow enrollment", "low_accrual"),
        ("Failure to achieve completion of enrollment", "low_accrual"),
        ("Stopped before enrollment was completed", "low_accrual"),
        ("Enrollment could not be completed", "low_accrual"),
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
