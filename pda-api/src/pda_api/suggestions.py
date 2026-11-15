"""Design-change suggestions, the what-if engine and the evidence validator.

Every number shown in a suggestion comes from ``metrics_for``, which computes it from the
benchmark dataset and the seeded forecast. The language model provider is never involved.
``validate`` recomputes those numbers and rejects a suggestion that cites fewer than
``MIN_CITED`` benchmark trials, cites a trial that does not support it, or shows a number
that the recomputation does not produce.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from statistics import median

from pda_api.benchmark import Benchmark, Trial
from pda_api.forecast import DEFAULT_SEED, forecast, reference_window
from pda_api.restrictiveness import DOMAINS, HIGH, LABELS, score_criterion, trial_window, width
from pda_api.schemas import (
    AppliedChange,
    Change,
    Criterion,
    Evidence,
    Forecast,
    PlannedCountry,
    ProtocolDesign,
    Suggestion,
)

MIN_CITED = 5
MAX_CITED = 10
MIN_COUNTRY_TRIALS = 5
MIN_SITES_ADDED = 5
MAX_SITES_ADDED = 30
MAX_SITE_SUGGESTIONS = 2
TOLERANCE = 1e-6
_NUMBER = re.compile(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?")


class ChangeError(ValueError):
    """A change cannot be applied to the design."""


@dataclass
class Context:
    """What a suggestion is computed from: the stored design and its benchmark."""

    design: ProtocolDesign
    similar: list[Trial]
    benchmark: Benchmark
    seed: int = DEFAULT_SEED
    _baseline: Forecast | None = field(default=None, repr=False)

    @property
    def baseline(self) -> Forecast:
        if self._baseline is None:
            self._baseline = forecast(self.design, self.similar, self.benchmark, seed=self.seed)
        return self._baseline

    def scenario(self, changes: list[Change]) -> Forecast:
        """Forecast after the changes, against the same benchmark trials and seed as the baseline."""
        return forecast(apply_changes(self.design, changes), self.similar, self.benchmark, seed=self.seed)

    def pool(self) -> list[Trial]:
        """Every benchmark trial of the design's indication and phase."""
        return [
            trial
            for trial in self.benchmark.trials
            if trial.indication == self.design.indication and trial.phase_group == self.design.phase_group
        ]


def fmt(value: float) -> str:
    """The one way a number is written in suggestion text: at most one decimal."""
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"


def _criterion(design: ProtocolDesign, criterion_id: str | None) -> Criterion:
    for criterion in design.criteria:
        if criterion.id == criterion_id:
            return criterion
    raise ChangeError(f"Unknown criterion: {criterion_id}")


def apply_changes(design: ProtocolDesign, changes: list[Change]) -> ProtocolDesign:
    """Return a copy of the design with the changes applied."""
    updated = design.model_copy(deep=True)
    for change in changes:
        if change.kind == "relax_criterion":
            criterion = _criterion(updated, change.criterion_id)
            if criterion.parameter not in DOMAINS:
                raise ChangeError(f"Criterion {criterion.id} has no numeric range to relax")
            criterion.lower, criterion.upper = change.lower, change.upper
            if criterion.parameter == "age":
                updated.population.min_age, updated.population.max_age = change.lower, change.upper
        else:
            if not change.country or not change.sites:
                raise ChangeError("Adding sites needs a country and a number of sites")
            for planned in updated.planned_countries:
                if planned.country == change.country:
                    planned.sites = (planned.sites or 0) + change.sites
                    break
            else:
                updated.planned_countries.append(PlannedCountry(country=change.country, sites=change.sites))
            updated.site_count = (updated.site_count or 0) + change.sites
    return updated


def describe(design: ProtocolDesign, change: Change) -> str:
    if change.kind == "add_sites":
        return f"Add {change.sites} sites in {change.country}"
    criterion = _criterion(design, change.criterion_id)
    label, unit = LABELS.get(criterion.parameter or "", (criterion.category, ""))
    return f"Relax {criterion.id} ({label}) to {_window(change.lower, change.upper)} {unit}".strip()


def applied(design: ProtocolDesign, changes: list[Change]) -> list[AppliedChange]:
    return [AppliedChange(change=change, summary=describe(design, change)) for change in changes]


def _window(lower: float | None, upper: float | None) -> str:
    if lower is not None and upper is not None:
        return f"{fmt(lower)} to {fmt(upper)}"
    return f"{fmt(lower)} or more" if lower is not None else f"up to {fmt(upper or 0)}"


def supporting_trials(context: Context, change: Change) -> list[Trial]:
    """Benchmark trials that back a change, most similar first where that order exists."""
    if change.kind == "add_sites":
        return sorted(
            (t for t in context.pool() if change.country in t.countries and t.accrual_rate_per_site_month),
            key=lambda trial: trial.nct_id,
        )
    criterion = _criterion(context.design, change.criterion_id)
    if criterion.parameter not in DOMAINS:
        return []
    mine = width(criterion.parameter, criterion.lower, criterion.upper)
    return [
        trial
        for trial in context.similar
        if (window := trial_window(criterion.parameter, trial)) is not None
        and width(criterion.parameter, *window) > mine
    ]


def metrics_for(context: Context, change: Change) -> dict[str, float]:
    """Every number a suggestion for ``change`` may show, computed from the dataset."""
    after = context.scenario([change])
    metrics = {
        "p50_months_before": context.baseline.p50_months,
        "p50_months_after": after.p50_months,
        "months_saved": round(context.baseline.p50_months - after.p50_months, 1),
        "supporting_trials": float(len(supporting_trials(context, change))),
    }
    if change.kind == "add_sites":
        with_sites = [float(trial.site_count) for trial in context.similar if trial.site_count]
        rates = [t.accrual_rate_per_site_month or 0.0 for t in supporting_trials(context, change)]
        metrics |= {
            "sites_added": float(change.sites or 0),
            "current_sites": float(context.design.site_count or 0),
            "median_similar_sites": float(median(with_sites)) if with_sites else 0.0,
            "country_median_rate": round(float(median(rates)), 1) if rates else 0.0,
        }
        return metrics
    criterion = _criterion(context.design, change.criterion_id)
    assert criterion.parameter is not None
    reference = reference_window(criterion.parameter, context.similar)
    metrics |= {
        "restrictiveness_score": float(score_criterion(criterion, context.design, context.similar).score),
        "trials_with_limit": float(reference.n_compared if reference else 0),
    }
    for name, value in (
        ("draft_lower", criterion.lower),
        ("draft_upper", criterion.upper),
        ("relaxed_lower", change.lower),
        ("relaxed_upper", change.upper),
    ):
        if value is not None:
            metrics[name] = float(value)
    return metrics


LABELS_BY_METRIC = {
    "p50_months_before": "P50 months to full enrollment today",
    "p50_months_after": "P50 months with this change",
    "months_saved": "P50 months saved",
    "supporting_trials": "Benchmark trials supporting the change",
    "sites_added": "Sites added",
    "current_sites": "Sites planned today",
    "median_similar_sites": "Median sites of similar trials",
    "country_median_rate": "Median patients per site per month of trials in the country",
    "restrictiveness_score": "Restrictiveness score of the criterion",
    "trials_with_limit": "Similar trials stating a limit",
    "draft_lower": "Draft lower limit",
    "draft_upper": "Draft upper limit",
    "relaxed_lower": "Median lower limit of similar trials",
    "relaxed_upper": "Median upper limit of similar trials",
}


def _build(context: Context, change: Change, identifier: str) -> Suggestion:
    m = metrics_for(context, change)
    saved = f"The P50 forecast moves from {fmt(m['p50_months_before'])} to {fmt(m['p50_months_after'])} months."
    if change.kind == "add_sites":
        title = describe(context.design, change)
        rationale = (
            f"The draft plans {fmt(m['current_sites'])} sites; similar trials used a median of "
            f"{fmt(m['median_similar_sites'])}. {fmt(m['supporting_trials'])} benchmark trials of this indication "
            f"and phase ran sites in {change.country}, with a median of {fmt(m['country_median_rate'])} patients "
            f"per site per month. {saved}"
        )
    else:
        criterion = _criterion(context.design, change.criterion_id)
        label, unit = LABELS[criterion.parameter or ""]
        title = describe(context.design, change)
        rationale = (
            f"The draft allows {label} {_window(criterion.lower, criterion.upper)} {unit} and scores "
            f"{fmt(m['restrictiveness_score'])} for restrictiveness. {fmt(m['supporting_trials'])} of "
            f"{fmt(m['trials_with_limit'])} similar trials with a stated limit allow a wider range; their median "
            f"window is {_window(change.lower, change.upper)} {unit}. {saved}"
        )
    return Suggestion(
        id=identifier,
        title=title,
        rationale=rationale,
        change=change,
        evidence=[Evidence(metric=name, label=LABELS_BY_METRIC[name], value=value) for name, value in m.items()],
        cited_trial_ids=[trial.nct_id for trial in supporting_trials(context, change)[:MAX_CITED]],
        p50_months_after=m["p50_months_after"],
        months_saved=m["months_saved"],
    )


def validate(suggestion: Suggestion, context: Context) -> list[str]:
    """Return the reasons a suggestion is not backed by the dataset. Empty means it passes."""
    problems = []
    cited = suggestion.cited_trial_ids
    if len(set(cited)) < MIN_CITED:
        problems.append(f"cites {len(set(cited))} benchmark trials, at least {MIN_CITED} are required")
    try:
        supporting = {trial.nct_id for trial in supporting_trials(context, suggestion.change)}
        expected = metrics_for(context, suggestion.change)
    except ChangeError as error:
        return [*problems, str(error)]
    known = context.benchmark.trial_ids()
    for trial_id in cited:
        if trial_id not in known:
            problems.append(f"{trial_id} is not in the benchmark dataset")
        elif trial_id not in supporting:
            problems.append(f"{trial_id} does not support this change")
    for item in suggestion.evidence:
        if item.metric not in expected:
            problems.append(f"'{item.metric}' is not a metric computed from the dataset")
        elif not math.isclose(item.value, expected[item.metric], abs_tol=TOLERANCE):
            problems.append(f"{item.metric} is {item.value:g}, the dataset gives {expected[item.metric]:g}")
    traceable = {fmt(value) for value in expected.values()}
    for text in (suggestion.title, suggestion.rationale):
        for number in _NUMBER.findall(text):
            if fmt(float(number)) not in traceable:
                problems.append(f"the number {number} in the text is not traceable to the dataset")
    for name, value in (("p50_months_after", suggestion.p50_months_after), ("months_saved", suggestion.months_saved)):
        if not math.isclose(value, expected[name], abs_tol=TOLERANCE):
            problems.append(f"{name} is {value:g}, the dataset gives {expected[name]:g}")
    return problems


def _relax_candidates(context: Context) -> list[Change]:
    changes = []
    for criterion in context.design.criteria:
        if criterion.parameter not in DOMAINS or (criterion.lower is None and criterion.upper is None):
            continue
        if score_criterion(criterion, context.design, context.similar).score < HIGH:
            continue
        reference = reference_window(criterion.parameter, context.similar)
        if reference is None:
            continue
        low, high = DOMAINS[criterion.parameter]
        lower = min(reference.lower, criterion.lower if criterion.lower is not None else low)
        upper = max(reference.upper, criterion.upper if criterion.upper is not None else high)
        changes.append(
            Change(
                kind="relax_criterion",
                criterion_id=criterion.id,
                lower=None if lower <= low else lower,
                upper=None if upper >= high else upper,
            )
        )
    return changes


def _site_candidates(context: Context) -> list[Change]:
    """Add sites where benchmark trials accrued fastest, up to the similar trials' median site count."""
    current = context.design.site_count or 0
    with_sites = [float(trial.site_count) for trial in context.similar if trial.site_count]
    if not with_sites:
        return []
    gap = float(median(with_sites)) - current
    if gap <= 0:
        return []
    rows = [
        row
        for row in context.benchmark.country_accrual
        if row.indication == context.design.indication
        and row.phase_group == context.design.phase_group
        and row.n_with_accrual_rate >= MIN_COUNTRY_TRIALS
        and row.accrual_rate_p50
    ]
    planned = {country.country for country in context.design.planned_countries}
    ranked = sorted(rows, key=lambda row: (row.country not in planned, -(row.accrual_rate_p50 or 0.0), row.country))
    sites = int(min(MAX_SITES_ADDED, max(MIN_SITES_ADDED, math.ceil(gap / MAX_SITE_SUGGESTIONS))))
    return [Change(kind="add_sites", country=row.country, sites=sites) for row in ranked[:MAX_SITE_SUGGESTIONS]]


def suggest(context: Context) -> tuple[list[Suggestion], int]:
    """Validated suggestions that shorten the forecast, best first, and the number rejected."""
    accepted, rejected = [], 0
    for index, change in enumerate([*_relax_candidates(context), *_site_candidates(context)], start=1):
        suggestion = _build(context, change, f"S{index}")
        if validate(suggestion, context) or suggestion.months_saved <= 0:
            rejected += 1
            continue
        accepted.append(suggestion)
    accepted.sort(key=lambda suggestion: (-suggestion.months_saved, suggestion.id))
    return accepted, rejected
