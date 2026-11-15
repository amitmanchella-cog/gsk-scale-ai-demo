from __future__ import annotations

from pda_api.benchmark import Benchmark
from pda_api.competing import competing_by_country, crowding
from pda_api.restrictiveness import level, score_criterion, score_design, summarise, width
from pda_api.schemas import Criterion, PlannedCountry, ProtocolDesign
from pda_api.similarity import find_similar


def _similar(design: ProtocolDesign, benchmark: Benchmark, limit: int = 40) -> list:  # type: ignore[type-arg]
    return [trial for trial, _ in find_similar(design, benchmark.trials, limit)]


def _age(lower: float, upper: float) -> Criterion:
    return Criterion(
        id="I1",
        kind="inclusion",
        text=f"Aged {lower:g} to {upper:g} years",
        category="age",
        parameter="age",
        lower=lower,
        upper=upper,
    )


def test_similar_trials_share_indication_and_phase(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    ranked = find_similar(weak_design, benchmark.trials)
    assert 20 <= len(ranked) <= 50
    assert {trial.indication for trial, _ in ranked} == {"type_2_diabetes"}
    assert {trial.phase_group for trial, _ in ranked} == {3}
    similarities = [similarity for _, similarity in ranked]
    assert similarities == sorted(similarities, reverse=True)
    assert all(0 < similarity <= 1 for similarity in similarities)
    assert len({trial.nct_id for trial, _ in ranked}) == len(ranked)


def test_similar_limit_is_clamped(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    assert len(find_similar(weak_design, benchmark.trials, 5)) == 20
    assert len(find_similar(weak_design, benchmark.trials, 500)) == 50


def test_similar_falls_back_to_other_phase_when_pool_is_small(
    weak_design: ProtocolDesign, benchmark: Benchmark
) -> None:
    phase3 = [t for t in benchmark.trials if t.indication == "type_2_diabetes" and t.phase_group == 3][:5]
    phase2 = [t for t in benchmark.trials if t.indication == "type_2_diabetes" and t.phase_group == 2][:30]
    ranked = find_similar(weak_design, tuple(phase3 + phase2))
    assert len(ranked) == 20
    assert [t.phase_group for t, _ in ranked[:5]] == [3] * 5


def test_score_rises_when_age_range_is_tightened(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    similar = _similar(weak_design, benchmark)
    wide = score_criterion(_age(18, 80), weak_design, similar)
    narrow = score_criterion(_age(18, 65), weak_design, similar)
    assert wide.basis == narrow.basis == "range"
    assert narrow.score > wide.score
    assert len(narrow.driving_trials) >= len(wide.driving_trials)


def test_score_rises_when_hba1c_range_is_tightened(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    similar = _similar(weak_design, benchmark)

    def hba1c(lower: float, upper: float) -> int:
        criterion = Criterion(
            id="I3", kind="inclusion", text="HbA1c", category="hba1c", parameter="hba1c", lower=lower, upper=upper
        )
        return score_criterion(criterion, weak_design, similar).score

    assert hba1c(7.5, 8.5) > hba1c(7.0, 10.0) >= hba1c(6.5, 12.0)


def test_weak_protocol_has_red_flags_with_driving_trials(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    similar = _similar(weak_design, benchmark)
    scores = {score.criterion_id: score for score in score_design(weak_design, similar)}
    assert len(scores) == len(weak_design.criteria)
    for criterion_id in ("I1", "I3", "I4", "I6"):
        assert scores[criterion_id].level == "high", scores[criterion_id]
    known = benchmark.trial_ids()
    for score in scores.values():
        assert 0 <= score.score <= 100
        assert {trial.nct_id for trial in score.driving_trials} <= known
        if score.score > 0:
            assert score.driving_trials, score
    assert scores["E12"].basis == "prevalence" and scores["E12"].level == "low"
    assert scores["E15"].basis == "burden"


def test_range_falls_back_to_prevalence_without_enough_comparators(
    weak_design: ProtocolDesign, benchmark: Benchmark
) -> None:
    similar = [trial for trial in _similar(weak_design, benchmark) if "fev1_pct" not in trial.thresholds]
    criterion = Criterion(
        id="I9", kind="inclusion", text="FEV1 > 50%", category="fev1_pct", parameter="fev1_pct", lower=50
    )
    assert score_criterion(criterion, weak_design, similar).basis == "prevalence"


def test_width_and_levels() -> None:
    assert width("age", 18, None) == 82
    assert width("age", None, None) == 100
    assert width("hba1c", 7, 10) == 3
    assert [level(score) for score in (0, 39, 40, 69, 70, 100)] == [
        "low",
        "low",
        "moderate",
        "moderate",
        "high",
        "high",
    ]


def test_summary_medians(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    summary = summarise(_similar(weak_design, benchmark))
    assert summary.n_similar == 40
    assert summary.median_enrollment > 0 and summary.median_duration_months > 0
    assert summarise([]).median_site_count is None


def test_competing_trials_per_country(weak_design: ProtocolDesign, benchmark: Benchmark) -> None:
    countries = competing_by_country(weak_design, benchmark.recruiting)
    assert [c.country for c in countries] == ["United States", "China"]
    for country in countries:
        assert country.crowding == "high"
        assert country.competing_trials >= len(country.trials) > 0
        sites = [trial.sites_in_country for trial in country.trials]
        assert sites == sorted(sites, reverse=True)
    nowhere = weak_design.model_copy(update={"planned_countries": [PlannedCountry(country="Atlantis", sites=1)]})
    empty = competing_by_country(nowhere, benchmark.recruiting)[0]
    assert (empty.competing_trials, empty.crowding, empty.trials) == (0, "low", [])
    assert [crowding(n) for n in (0, 3, 4, 9, 10)] == ["low", "low", "moderate", "moderate", "high"]
