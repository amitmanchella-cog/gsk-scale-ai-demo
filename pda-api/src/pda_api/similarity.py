"""Find the benchmark trials most similar to a draft design."""

from __future__ import annotations

import math

from pda_api.benchmark import Trial
from pda_api.schemas import ProtocolDesign, SimilarTrial

MIN_SIMILAR = 20
MAX_SIMILAR = 50
DEFAULT_SIMILAR = 40


def _log_ratio(a: float | None, b: float | None, missing: float) -> float:
    if not a or not b:
        return missing
    return abs(math.log(a / b))


def distance(design: ProtocolDesign, trial: Trial) -> float:
    """Smaller is more similar: enrollment, age window and criteria mix.

    Site count is deliberately left out: it is a design lever the advisor varies, and
    matching on it would bias the benchmark accrual rates used by the forecast.
    """
    age = (
        abs((design.population.min_age or 0.0) - (trial.min_age_years or 0.0))
        + abs((design.population.max_age or 100.0) - (trial.max_age_years or 100.0))
    ) / 40.0
    mine = {criterion.category for criterion in design.criteria} - {"age", "other", "consent"}
    theirs = set(trial.categories)
    union = mine | theirs
    jaccard = 1.0 - (len(mine & theirs) / len(union)) if union else 0.0
    return _log_ratio(design.target_enrollment, trial.enrollment, 1.0) + age + 0.5 * jaccard


def find_similar(
    design: ProtocolDesign, trials: tuple[Trial, ...], limit: int = DEFAULT_SIMILAR
) -> list[tuple[Trial, float]]:
    """Return the ``limit`` nearest trials of the same indication and phase, with a 0-1 similarity.

    If fewer than 20 trials share the phase, the other phase of the same indication fills the gap.
    """
    limit = max(MIN_SIMILAR, min(MAX_SIMILAR, limit))
    same_indication = [trial for trial in trials if trial.indication == design.indication]
    pool = [trial for trial in same_indication if trial.phase_group == design.phase_group]
    ranked = sorted(pool, key=lambda trial: (distance(design, trial), trial.nct_id))[:limit]
    if len(ranked) < MIN_SIMILAR:
        others = [trial for trial in same_indication if trial.phase_group != design.phase_group]
        ranked += sorted(others, key=lambda trial: (distance(design, trial), trial.nct_id))[: MIN_SIMILAR - len(ranked)]
    return [(trial, round(1.0 / (1.0 + distance(design, trial)), 4)) for trial in ranked]


def to_schema(trial: Trial, similarity: float) -> SimilarTrial:
    return SimilarTrial(
        nct_id=trial.nct_id,
        title=trial.title,
        phase=trial.phase,
        overall_status=trial.overall_status,
        stop_category=trial.stop_category,
        enrollment=trial.enrollment,
        site_count=trial.site_count,
        duration_months=trial.duration_months,
        accrual_rate_per_site_month=trial.accrual_rate_per_site_month,
        min_age_years=trial.min_age_years,
        max_age_years=trial.max_age_years,
        similarity=similarity,
    )
