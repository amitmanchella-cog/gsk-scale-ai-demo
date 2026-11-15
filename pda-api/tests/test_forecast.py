from __future__ import annotations

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from pda_api.benchmark import Benchmark, Trial
from pda_api.forecast import (
    ForecastError,
    eligibility_factors,
    forecast,
    months_to_target,
    ramp_months,
    rate_multiplier,
    termination_risk,
)
from pda_api.schemas import Change, PlannedCountry, ProtocolDesign
from pda_api.similarity import find_similar
from pda_api.suggestions import MIN_CITED, ChangeError, Context, apply_changes, fmt, suggest, validate
from tests.conftest import upload


@pytest.fixture(scope="module")
def similar(weak_design: ProtocolDesign, benchmark: Benchmark) -> list[Trial]:
    return [trial for trial, _ in find_similar(weak_design, benchmark.trials, 40)]


@pytest.fixture(scope="module")
def context(weak_design: ProtocolDesign, similar: list[Trial], benchmark: Benchmark) -> Context:
    return Context(design=weak_design, similar=similar, benchmark=benchmark)


def _with_sites(design: ProtocolDesign, sites: int) -> ProtocolDesign:
    return design.model_copy(update={"site_count": sites})


# --- Monte Carlo forecast ---------------------------------------------------------------


def test_forecast_is_reproducible_with_a_fixed_seed(
    weak_design: ProtocolDesign, similar: list[Trial], benchmark: Benchmark
) -> None:
    first = forecast(weak_design, similar, benchmark, seed=7)
    again = forecast(weak_design, similar, benchmark, seed=7)
    other = forecast(weak_design, similar, benchmark, seed=8)
    assert first == again
    assert (first.p50_months, first.p90_months) != (other.p50_months, other.p90_months)


def test_p50_is_below_p90(weak_design: ProtocolDesign, similar: list[Trial], benchmark: Benchmark) -> None:
    result = forecast(weak_design, similar, benchmark)
    assert 0 < result.p50_months < result.p90_months


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_more_sites_shorten_the_forecast(
    weak_design: ProtocolDesign, similar: list[Trial], benchmark: Benchmark, seed: int
) -> None:
    results = [forecast(_with_sites(weak_design, sites), similar, benchmark, seed=seed) for sites in (8, 16, 40)]
    assert results[0].p50_months > results[1].p50_months > results[2].p50_months
    assert results[0].p90_months > results[1].p90_months > results[2].p90_months


def test_site_activation_ramp_delays_enrollment(
    weak_design: ProtocolDesign, similar: list[Trial], benchmark: Benchmark
) -> None:
    design = _with_sites(weak_design.model_copy(update={"target_enrollment": 60}), 40)
    flat = forecast(design, similar, benchmark, ramp=0.0)
    ramped = forecast(design, similar, benchmark)
    assert ramped.ramp_months == 6.0
    assert flat.p50_months < ramped.p50_months


def test_ramp_window_grows_with_site_count() -> None:
    assert [ramp_months(sites) for sites in (1, 25, 49, 50, 100, 1000)] == [6.0, 6.0, 6.0, 7.0, 9.0, 18.0]


def test_months_to_target_is_exact_for_staggered_sites() -> None:
    # Site A: 10/month from month 0. Site B: 10/month from month 2. 100 patients -> 20 by month 2, then 20/month.
    rates = np.array([[10.0], [10.0]])
    activation = np.array([[0.0], [2.0]])
    assert months_to_target(rates, activation, 100)[0] == pytest.approx(6.0)
    assert months_to_target(rates, activation, 10)[0] == pytest.approx(1.0)


def test_forecast_needs_enrollment_and_sites(similar: list[Trial], benchmark: Benchmark) -> None:
    with pytest.raises(ForecastError):
        forecast(ProtocolDesign(indication="asthma", phase_group=3), similar, benchmark)


def test_falls_back_to_the_pda_data_percentiles_without_similar_rates(
    weak_design: ProtocolDesign, benchmark: Benchmark
) -> None:
    result = forecast(weak_design, [], benchmark)
    assert result.rate_source == "indication_phase_benchmark"
    row = benchmark.accrual_for("type_2_diabetes", 3)
    assert row is not None
    assert row.percentiles[10] <= result.median_benchmark_rate <= row.percentiles[90]
    assert result.indication_phase_median_rate == pytest.approx(row.percentiles[50], abs=1e-3)


# --- eligibility and termination risk ----------------------------------------------------


def test_narrow_windows_slow_the_forecast_and_relaxing_one_helps(context: Context) -> None:
    factors = eligibility_factors(context.design, context.similar)
    assert {f.criterion_id for f in factors if f.factor < 1} >= {"I1", "I3"}
    assert 0.25 <= rate_multiplier(factors) < 1
    age = next(f for f in factors if f.criterion_id == "I1")
    relaxed = context.scenario(
        [Change(kind="relax_criterion", criterion_id="I1", lower=age.reference_lower, upper=age.reference_upper)]
    )
    assert relaxed.rate_multiplier > context.baseline.rate_multiplier
    assert relaxed.p50_months < context.baseline.p50_months


def test_termination_risk_is_the_low_accrual_share_adjusted_by_the_forecast(
    weak_design: ProtocolDesign, similar: list[Trial], benchmark: Benchmark
) -> None:
    slow = termination_risk(similar, benchmark, weak_design, p50=200.0)
    fast = termination_risk(similar, benchmark, weak_design, p50=5.0)
    low = sum(trial.low_accrual_terminated for trial in similar)
    row = benchmark.accrual_for("type_2_diabetes", 3)
    assert row is not None
    assert slow.baseline_share == pytest.approx((low + 20 * row.low_accrual_terminated_share) / 60, abs=1e-4)
    assert (slow.adjustment, fast.adjustment) == (4.0, 0.5)
    assert slow.risk == pytest.approx(slow.baseline_share * 4, abs=1e-3)
    assert 0 < fast.risk < slow.risk <= 0.95
    assert (slow.level, fast.level) == ("high", "low")
    by_id = benchmark.by_id()
    assert slow.trial_ids and all(by_id[trial_id].low_accrual_terminated for trial_id in slow.trial_ids)


# --- suggestions and the evidence validator ---------------------------------------------


def test_every_suggestion_cites_five_trials_and_passes_the_validator(context: Context) -> None:
    suggestions, _ = suggest(context)
    kinds = {suggestion.change.kind for suggestion in suggestions}
    assert kinds == {"relax_criterion", "add_sites"}
    known = context.benchmark.trial_ids()
    for suggestion in suggestions:
        assert len(set(suggestion.cited_trial_ids)) >= MIN_CITED
        assert set(suggestion.cited_trial_ids) <= known
        assert validate(suggestion, context) == []
        assert suggestion.months_saved > 0
    saved = [suggestion.months_saved for suggestion in suggestions]
    assert saved == sorted(saved, reverse=True)


def test_validator_rejects_fewer_than_five_cited_trials(context: Context) -> None:
    suggestion = suggest(context)[0][0]
    short = suggestion.model_copy(update={"cited_trial_ids": suggestion.cited_trial_ids[:4]})
    assert any("at least 5" in problem for problem in validate(short, context))


def test_validator_rejects_a_number_not_traceable_to_the_dataset(context: Context) -> None:
    suggestion = suggest(context)[0][0]
    invented_text = suggestion.model_copy(update={"rationale": suggestion.rationale + " Expect 37.5% faster accrual."})
    assert any("37.5" in problem for problem in validate(invented_text, context))

    evidence = [item.model_copy() for item in suggestion.evidence]
    evidence[0].value += 3
    assert any(
        "the dataset gives" in problem
        for problem in validate(suggestion.model_copy(update={"evidence": evidence}), context)
    )

    unknown = [*suggestion.evidence, suggestion.evidence[0].model_copy(update={"metric": "llm_estimate"})]
    assert any(
        "llm_estimate" in problem for problem in validate(suggestion.model_copy(update={"evidence": unknown}), context)
    )

    better = suggestion.model_copy(update={"months_saved": suggestion.months_saved + 12})
    assert any("months_saved" in problem for problem in validate(better, context))


def test_validator_rejects_cited_trials_that_do_not_support_the_change(context: Context) -> None:
    suggestion = suggest(context)[0][0]
    fake = suggestion.model_copy(update={"cited_trial_ids": [f"NCT0000000{i}" for i in range(5)]})
    assert any("not in the benchmark dataset" in problem for problem in validate(fake, context))
    other_indication = [trial.nct_id for trial in context.benchmark.trials if trial.indication == "asthma"][:5]
    unrelated = suggestion.model_copy(update={"cited_trial_ids": other_indication})
    assert any("does not support" in problem for problem in validate(unrelated, context))


def test_every_number_in_suggestion_text_is_in_the_evidence(context: Context) -> None:
    import re

    for suggestion in suggest(context)[0]:
        shown = {fmt(item.value) for item in suggestion.evidence}
        for number in re.findall(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?", suggestion.title + " " + suggestion.rationale):
            assert fmt(float(number)) in shown, (number, suggestion.rationale)


def test_apply_changes(weak_design: ProtocolDesign) -> None:
    changed = apply_changes(
        weak_design,
        [
            Change(kind="relax_criterion", criterion_id="I1", lower=18, upper=75),
            Change(kind="add_sites", country="China", sites=5),
            Change(kind="add_sites", country="Poland", sites=4),
        ],
    )
    assert (changed.population.min_age, changed.population.max_age) == (18, 75)
    assert changed.site_count == (weak_design.site_count or 0) + 9
    assert PlannedCountry(country="Poland", sites=4) in changed.planned_countries
    assert next(c.sites for c in changed.planned_countries if c.country == "China") == 8
    assert weak_design.site_count == 8  # the stored design is untouched
    with pytest.raises(ChangeError):
        apply_changes(weak_design, [Change(kind="relax_criterion", criterion_id="I99")])
    with pytest.raises(ChangeError):
        apply_changes(weak_design, [Change(kind="add_sites", country="China")])


# --- API ---------------------------------------------------------------------------------


def test_forecast_endpoint(client: TestClient) -> None:
    protocol_id = upload(client)
    body = client.get(f"/api/protocols/{protocol_id}/forecast").json()
    assert body["p50_months"] < body["p90_months"]
    assert body["sites"] == 8 and body["target_enrollment"] == 900
    assert 0 < body["termination_risk"]["risk"] <= 0.95
    assert client.get(f"/api/protocols/{protocol_id}/forecast?seed=5").json()["seed"] == 5
    assert body == client.get(f"/api/protocols/{protocol_id}/forecast").json()


def test_suggestions_endpoint(client: TestClient) -> None:
    protocol_id = upload(client)
    body = client.get(f"/api/protocols/{protocol_id}/suggestions").json()
    assert len(body["suggestions"]) >= 2
    assert all(len(suggestion["cited_trial_ids"]) >= 5 for suggestion in body["suggestions"])
    assert body["baseline"]["p50_months"] == client.get(f"/api/protocols/{protocol_id}/forecast").json()["p50_months"]


def test_what_if_applies_two_changes_and_improves_in_under_five_seconds(client: TestClient) -> None:
    protocol_id = upload(client)
    suggestions = client.get(f"/api/protocols/{protocol_id}/suggestions").json()["suggestions"]
    changes = [suggestion["change"] for suggestion in suggestions[:2]]
    started = time.perf_counter()
    response = client.post(f"/api/protocols/{protocol_id}/what-if", json={"changes": changes})
    elapsed = time.perf_counter() - started
    assert response.status_code == 200, response.text
    body = response.json()
    assert elapsed < 5 and body["elapsed_ms"] < 5000
    assert body["scenario"]["p50_months"] < body["baseline"]["p50_months"]
    assert body["scenario"]["p90_months"] < body["baseline"]["p90_months"]
    assert body["p50_months_saved"] > max(suggestion["months_saved"] for suggestion in suggestions[:2])
    assert len(body["applied"]) == 2 and all(item["summary"] for item in body["applied"])
    # The stored protocol is not modified by a what-if.
    assert client.get(f"/api/protocols/{protocol_id}/forecast").json() == body["baseline"]


def test_what_if_rejects_an_unknown_criterion(client: TestClient) -> None:
    protocol_id = upload(client)
    change = {"kind": "relax_criterion", "criterion_id": "I99", "lower": 1, "upper": 2}
    response = client.post(f"/api/protocols/{protocol_id}/what-if", json={"changes": [change]})
    assert response.status_code == 422
    assert "I99" in response.json()["detail"]
