"""Score how restrictive each eligibility criterion is against similar benchmark trials.

Every score is 0-100 and comes with the trials that drive it:

* ``range``: numeric criteria (age, HbA1c, BMI, FEV1, pack-years, eGFR). The score is the
  share of similar trials whose eligible window is wider than the draft's.
* ``prevalence``: keyword categories (pregnancy, malignancy...). The score is the share of
  similar trials with no comparable criterion, so a rarely used criterion scores high.
* ``burden``: criteria that match no category. The score is the share of similar trials
  with fewer criteria in total than the draft.
"""

from __future__ import annotations

from statistics import median

from pda_api.benchmark import Trial
from pda_api.schemas import BenchmarkSummary, Criterion, CriterionScore, DrivingTrial, Level, ProtocolDesign

# Plausible domain of each numeric parameter; an open bound counts as the domain limit.
DOMAINS: dict[str, tuple[float, float]] = {
    "age": (0.0, 100.0),
    "hba1c": (4.0, 15.0),
    "bmi": (14.0, 60.0),
    "fev1_pct": (10.0, 130.0),
    "pack_years": (0.0, 100.0),
    "egfr": (10.0, 120.0),
}
LABELS = {
    "age": ("age", "years"),
    "hba1c": ("HbA1c", "%"),
    "bmi": ("BMI", "kg/m2"),
    "fev1_pct": ("FEV1", "% predicted"),
    "pack_years": ("smoking history", "pack-years"),
    "egfr": ("eGFR", "mL/min"),
}
PARAMETER_CATEGORY = {
    "hba1c": "hba1c",
    "bmi": "bmi",
    "fev1_pct": "fev1",
    "pack_years": "smoking_history",
    "egfr": "renal",
}
MIN_COMPARED = 5
MAX_DRIVING = 10
HIGH = 70
MODERATE = 40


def level(score: int) -> Level:
    return "high" if score >= HIGH else "moderate" if score >= MODERATE else "low"


def width(parameter: str, lower: float | None, upper: float | None) -> float:
    low, high = DOMAINS[parameter]
    return max(0.0, min(high, upper if upper is not None else high) - max(low, lower if lower is not None else low))


def _window(parameter: str, lower: float | None, upper: float | None) -> str:
    unit = LABELS[parameter][1]
    if lower is not None and upper is not None:
        return f"{lower:g} to {upper:g} {unit}"
    if lower is not None:
        return f"{lower:g} {unit} or more"
    if upper is not None:
        return f"up to {upper:g} {unit}"
    return "no limit"


def trial_window(parameter: str, trial: Trial) -> tuple[float | None, float | None] | None:
    if parameter == "age":
        return trial.min_age_years, trial.max_age_years
    return trial.thresholds.get(parameter)


def _percent(part: float, whole: int) -> int:
    return round(100 * part / whole) if whole else 0


def _prevalence(criterion: Criterion, category: str, similar: list[Trial]) -> CriterionScore:
    with_category = [trial for trial in similar if category in trial.categories]
    without = [trial for trial in similar if category not in trial.categories]
    score = _percent(len(without), len(similar))
    return CriterionScore(
        criterion_id=criterion.id,
        kind=criterion.kind,
        text=criterion.text,
        category=criterion.category,
        score=score,
        level=level(score),
        basis="prevalence",
        rationale=(
            f"{len(with_category)} of {len(similar)} similar trials have a comparable "
            f"{category.replace('_', ' ')} criterion; {len(without)} recruited without one."
        ),
        n_compared=len(similar),
        driving_trials=[
            DrivingTrial(nct_id=trial.nct_id, title=trial.title, detail=f"no {category.replace('_', ' ')} criterion")
            for trial in without[:MAX_DRIVING]
        ],
    )


def _burden(criterion: Criterion, design: ProtocolDesign, similar: list[Trial]) -> CriterionScore:
    mine = len(design.criteria)
    fewer = [trial for trial in similar if trial.n_criteria < mine]
    score = _percent(len(fewer), len(similar))
    return CriterionScore(
        criterion_id=criterion.id,
        kind=criterion.kind,
        text=criterion.text,
        category=criterion.category,
        score=score,
        level=level(score),
        basis="burden",
        rationale=(
            f"Not matched to a benchmark category. The draft has {mine} criteria; "
            f"{len(fewer)} of {len(similar)} similar trials have fewer."
        ),
        n_compared=len(similar),
        driving_trials=[
            DrivingTrial(nct_id=trial.nct_id, title=trial.title, detail=f"{trial.n_criteria} criteria in total")
            for trial in fewer[:MAX_DRIVING]
        ],
    )


def _range(criterion: Criterion, parameter: str, similar: list[Trial]) -> CriterionScore | None:
    compared = [(trial, window) for trial in similar if (window := trial_window(parameter, trial)) is not None]
    if len(compared) < MIN_COMPARED:
        return None
    mine = width(parameter, criterion.lower, criterion.upper)
    wider = [(trial, window) for trial, window in compared if width(parameter, *window) > mine]
    score = _percent(len(wider), len(compared))
    label = LABELS[parameter][0]
    return CriterionScore(
        criterion_id=criterion.id,
        kind=criterion.kind,
        text=criterion.text,
        category=criterion.category,
        score=score,
        level=level(score),
        basis="range",
        rationale=(
            f"The draft allows {label} {_window(parameter, criterion.lower, criterion.upper)}. "
            f"{len(wider)} of {len(compared)} similar trials with a stated {label} limit allow a wider range."
        ),
        n_compared=len(compared),
        driving_trials=[
            DrivingTrial(nct_id=trial.nct_id, title=trial.title, detail=f"allows {label} {_window(parameter, *window)}")
            for trial, window in wider[:MAX_DRIVING]
        ],
    )


def score_criterion(criterion: Criterion, design: ProtocolDesign, similar: list[Trial]) -> CriterionScore:
    """Score one criterion. ``similar`` must be ordered from most to least similar."""
    if criterion.parameter in DOMAINS and (criterion.lower is not None or criterion.upper is not None):
        ranged = _range(criterion, criterion.parameter, similar)
        if ranged:
            return ranged
    category = PARAMETER_CATEGORY.get(criterion.category, criterion.category)
    if category in {"other", "age"}:
        return _burden(criterion, design, similar)
    return _prevalence(criterion, category, similar)


def _median(values: list[float]) -> float | None:
    return round(float(median(values)), 2) if values else None


def summarise(similar: list[Trial]) -> BenchmarkSummary:
    return BenchmarkSummary(
        n_similar=len(similar),
        median_enrollment=_median([float(trial.enrollment) for trial in similar]) or 0.0,
        median_site_count=_median([float(trial.site_count) for trial in similar if trial.site_count]),
        median_duration_months=_median([trial.duration_months for trial in similar]) or 0.0,
        median_accrual_rate_per_site_month=_median(
            [trial.accrual_rate_per_site_month for trial in similar if trial.accrual_rate_per_site_month]
        ),
        median_criteria_count=_median([float(trial.n_criteria) for trial in similar]) or 0.0,
    )


def score_design(design: ProtocolDesign, similar: list[Trial]) -> list[CriterionScore]:
    return [score_criterion(criterion, design, similar) for criterion in design.criteria]
