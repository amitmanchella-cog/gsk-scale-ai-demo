"""Seeded Monte Carlo forecast of months to full enrollment, and low-accrual termination risk.

Model (assumptions are listed in the README and in the clarifying comment on MBA-3860):

* Each simulation draws one benchmark accrual rate (patients per site per month) from the
  similar trials. If fewer than ``MIN_RATES`` similar trials have a usable rate, rates are
  drawn from the indication and phase percentiles published by pda-data instead.
* Each site gets that rate times its own gamma-distributed multiplier (mean 1), and its own
  activation month drawn uniformly over the ramp window. A site enrolls nothing before it opens.
* The rate is multiplied by an eligibility factor when the draft's numeric windows are
  narrower than the benchmark's (see ``eligibility_factors``).
* The result of one simulation is the month in which cumulative enrollment reaches the target.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

import numpy as np
from numpy.typing import NDArray

from pda_api.benchmark import Benchmark, Trial
from pda_api.restrictiveness import DOMAINS, MIN_COMPARED, level, trial_window, width
from pda_api.schemas import Criterion, EligibilityFactor, Forecast, ProtocolDesign, TerminationRisk

DEFAULT_SEED = 20260115
SIMULATIONS = 2000
MIN_RATES = 10
SITE_SHAPE = 2.0  # gamma shape of the site-to-site multiplier
BASE_RAMP_MONTHS = 6.0
RAMP_SITES_STEP = 25
MAX_RAMP_MONTHS = 18.0
MIN_RATE_MULTIPLIER = 0.25
RISK_PRIOR_WEIGHT = 20  # the indication and phase share counts as this many extra similar trials
MIN_ADJUSTMENT, MAX_ADJUSTMENT = 0.5, 4.0
MAX_RISK = 0.95

Floats = NDArray[np.float64]


class ForecastError(ValueError):
    """The design lacks what a forecast needs."""


@dataclass(frozen=True)
class Reference:
    """Median eligibility window of the similar trials that state a limit for a parameter."""

    lower: float
    upper: float
    n_compared: int


def ramp_months(sites: int) -> float:
    """Months over which sites open: 6, plus 1 per 25 sites above 25, at most 18."""
    return min(MAX_RAMP_MONTHS, BASE_RAMP_MONTHS + max(0, sites - RAMP_SITES_STEP) // RAMP_SITES_STEP)


def usable_rates(trials: list[Trial]) -> list[float]:
    return [t.accrual_rate_per_site_month for t in trials if t.accrual_rate_per_site_month]


def reference_window(parameter: str, similar: list[Trial]) -> Reference | None:
    low, high = DOMAINS[parameter]
    windows = [window for trial in similar if (window := trial_window(parameter, trial)) is not None]
    if len(windows) < MIN_COMPARED:
        return None
    return Reference(
        lower=float(median(lower if lower is not None else low for lower, _ in windows)),
        upper=float(median(upper if upper is not None else high for _, upper in windows)),
        n_compared=len(windows),
    )


def eligibility_factor(criterion: Criterion, reference: Reference) -> float:
    """Share of the reference window the draft still allows, assuming patients are spread evenly across it."""
    assert criterion.parameter is not None
    span = width(criterion.parameter, reference.lower, reference.upper)
    if span <= 0:
        return 1.0
    low, high = DOMAINS[criterion.parameter]
    lower = max(reference.lower, criterion.lower if criterion.lower is not None else low)
    upper = min(reference.upper, criterion.upper if criterion.upper is not None else high)
    return round(max(0.0, upper - lower) / span, 4)


def eligibility_factors(design: ProtocolDesign, similar: list[Trial]) -> list[EligibilityFactor]:
    factors = []
    for criterion in design.criteria:
        if criterion.parameter not in DOMAINS or (criterion.lower is None and criterion.upper is None):
            continue
        reference = reference_window(criterion.parameter, similar)
        if reference is None:
            continue
        factors.append(
            EligibilityFactor(
                criterion_id=criterion.id,
                parameter=criterion.parameter,
                factor=eligibility_factor(criterion, reference),
                reference_lower=reference.lower,
                reference_upper=reference.upper,
                n_compared=reference.n_compared,
            )
        )
    return factors


def rate_multiplier(factors: list[EligibilityFactor]) -> float:
    """Geometric mean of the factors of all compared numeric criteria, floored at 0.25.

    A plain product would double count, because narrow windows exclude overlapping patients.
    Criteria that are not narrower than the benchmark count as 1, so relaxing any one
    criterion can only raise the multiplier.
    """
    if not factors:
        return 1.0
    logs = [np.log(max(f.factor, 1e-6)) for f in factors]
    return round(max(MIN_RATE_MULTIPLIER, float(np.exp(np.mean(logs)))), 4)


def _benchmark_rates(benchmark: Benchmark, design: ProtocolDesign, rng: np.random.Generator, n: int) -> Floats:
    """Draw from the pda-data percentiles by interpolating the inverse CDF."""
    row = benchmark.accrual_for(design.indication, design.phase_group)
    if row is None or len(row.percentiles) < 2:
        raise ForecastError("No accrual benchmark is available for this indication and phase")
    points = sorted(row.percentiles.items())
    quantiles = rng.uniform(points[0][0], points[-1][0], n)
    return np.interp(quantiles, [p for p, _ in points], [v for _, v in points])


def months_to_target(rates: Floats, activation: Floats, target: int) -> Floats:
    """Month at which sum_i rates[i] * max(0, t - activation[i]) reaches ``target``, per simulation.

    Both arrays are (sites, simulations). Enrollment is piecewise linear in t, so the answer is exact.
    """
    order = np.argsort(activation, axis=0)
    opened = np.take_along_axis(activation, order, axis=0)
    site_rates = np.take_along_axis(rates, order, axis=0)
    cumulative_rate = np.cumsum(site_rates, axis=0)
    offset = np.cumsum(site_rates * opened, axis=0)
    finish = (target + offset) / cumulative_rate  # valid if it falls before the next site opens
    next_open = np.vstack([opened[1:], np.full((1, opened.shape[1]), np.inf)])
    segment = np.argmax(finish <= next_open, axis=0)
    result: Floats = np.take_along_axis(finish, segment[None, :], axis=0)[0]
    return result


def simulate(
    design: ProtocolDesign,
    similar: list[Trial],
    benchmark: Benchmark,
    *,
    seed: int = DEFAULT_SEED,
    simulations: int = SIMULATIONS,
    ramp: float | None = None,
    multiplier: float | None = None,
) -> tuple[Floats, dict[str, float | int | str]]:
    """Run the simulation and return months per simulation plus the inputs that were used."""
    if not design.target_enrollment or not design.site_count:
        raise ForecastError("The design needs a target enrollment and a site count for a forecast")
    sites, target = design.site_count, design.target_enrollment
    rates = usable_rates(similar)
    rate_rng, site_rng, ramp_rng = (np.random.default_rng([seed, stream]) for stream in range(3))
    if len(rates) >= MIN_RATES:
        source = "similar_trials"
        trial_rates = rate_rng.choice(np.asarray(sorted(rates)), size=simulations, replace=True)
    else:
        source = "indication_phase_benchmark"
        trial_rates = _benchmark_rates(benchmark, design, rate_rng, simulations)
    if multiplier is None:
        multiplier = rate_multiplier(eligibility_factors(design, similar))
    window = ramp_months(sites) if ramp is None else ramp
    # Row-major draws: the first k sites get the same numbers whatever the site count.
    site_factor = site_rng.gamma(SITE_SHAPE, 1.0 / SITE_SHAPE, size=(sites, simulations))
    activation = ramp_rng.uniform(0.0, 1.0, size=(sites, simulations)) * window
    months = months_to_target(site_factor * trial_rates[None, :] * multiplier, activation, target)
    inputs: dict[str, float | int | str] = {
        "source": source,
        "n_rates": len(rates) if source == "similar_trials" else 0,
        "median_rate": float(np.median(trial_rates)),
        "multiplier": multiplier,
        "ramp": window,
    }
    return months, inputs


def termination_risk(similar: list[Trial], benchmark: Benchmark, design: ProtocolDesign, p50: float) -> TerminationRisk:
    """Share of similar trials terminated for low accrual, adjusted by how slow the forecast is.

    The share is smoothed towards the indication and phase share from pda-data so that a
    sample of 20-50 trials with no such termination does not report a risk of exactly zero.
    """
    low = [trial for trial in similar if trial.low_accrual_terminated]
    row = benchmark.accrual_for(design.indication, design.phase_group)
    prior = row.low_accrual_terminated_share if row else 0.0
    baseline = (len(low) + prior * RISK_PRIOR_WEIGHT) / (len(similar) + RISK_PRIOR_WEIGHT)
    typical = float(median(trial.duration_months for trial in similar)) if similar else p50
    adjustment = min(MAX_ADJUSTMENT, max(MIN_ADJUSTMENT, p50 / typical)) if typical > 0 else 1.0
    cited = low or [
        trial
        for trial in benchmark.trials
        if trial.low_accrual_terminated
        and trial.indication == design.indication
        and trial.phase_group == design.phase_group
    ]
    return TerminationRisk(
        risk=round(min(MAX_RISK, baseline * adjustment), 4),
        level=level(round(100 * (adjustment - 1) / 1.5 + 25)) if adjustment > 1 else "low",
        baseline_share=round(baseline, 4),
        similar_low_accrual=len(low),
        n_similar=len(similar),
        indication_phase_share=round(prior, 4),
        adjustment=round(adjustment, 2),
        trial_ids=sorted(trial.nct_id for trial in cited)[:10],
    )


def forecast(
    design: ProtocolDesign,
    similar: list[Trial],
    benchmark: Benchmark,
    *,
    seed: int = DEFAULT_SEED,
    simulations: int = SIMULATIONS,
    ramp: float | None = None,
) -> Forecast:
    """P50 and P90 months to full enrollment. ``similar`` is the benchmark the rates come from."""
    factors = eligibility_factors(design, similar)
    months, inputs = simulate(
        design, similar, benchmark, seed=seed, simulations=simulations, ramp=ramp, multiplier=rate_multiplier(factors)
    )
    p50, p90 = (round(float(np.percentile(months, q)), 1) for q in (50, 90))
    row = benchmark.accrual_for(design.indication, design.phase_group)
    assert design.target_enrollment and design.site_count
    return Forecast(
        p50_months=p50,
        p90_months=p90,
        target_enrollment=design.target_enrollment,
        sites=design.site_count,
        ramp_months=float(inputs["ramp"]),
        rate_multiplier=float(inputs["multiplier"]),
        eligibility_factors=factors,
        rate_source=inputs["source"],  # type: ignore[arg-type]
        n_rates=int(inputs["n_rates"]),
        median_benchmark_rate=round(float(inputs["median_rate"]), 3),
        indication_phase_median_rate=round(row.percentiles[50], 3) if row and 50 in row.percentiles else None,
        simulations=simulations,
        seed=seed,
        termination_risk=termination_risk(similar, benchmark, design, p50),
    )
