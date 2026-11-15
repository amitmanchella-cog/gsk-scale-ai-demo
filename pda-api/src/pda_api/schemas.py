"""API and domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Indication = Literal["asthma", "copd", "type_2_diabetes"]
Level = Literal["low", "moderate", "high"]


class Criterion(BaseModel):
    id: str = Field(description="I1, I2... for inclusion, E1, E2... for exclusion")
    kind: Literal["inclusion", "exclusion"]
    text: str
    category: str = Field(description="Keyword category, a numeric parameter name, 'age' or 'other'")
    parameter: str | None = Field(default=None, description="Numeric parameter the criterion constrains")
    lower: float | None = Field(default=None, description="Lower bound of the eligible range")
    upper: float | None = Field(default=None, description="Upper bound of the eligible range")


class PlannedCountry(BaseModel):
    country: str
    sites: int | None = None


class Population(BaseModel):
    min_age: float | None = None
    max_age: float | None = None
    sex: Literal["ALL", "FEMALE", "MALE"] = "ALL"
    healthy_volunteers: bool = False
    summary: str | None = None


class ProtocolDesign(BaseModel):
    title: str | None = None
    indication: Indication | None = None
    phase: str | None = None
    phase_group: int | None = None
    population: Population = Field(default_factory=Population)
    target_enrollment: int | None = None
    planned_countries: list[PlannedCountry] = Field(default_factory=list)
    site_count: int | None = None
    criteria: list[Criterion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProtocolOut(BaseModel):
    id: str
    document: str
    created_at: datetime
    design: ProtocolDesign


class SampleProtocol(BaseModel):
    key: str
    filename: str
    title: str
    indication: str | None
    weak: bool


class SimilarTrial(BaseModel):
    nct_id: str
    title: str | None
    phase: str
    overall_status: str
    stop_category: str
    enrollment: int
    site_count: int | None
    duration_months: float
    accrual_rate_per_site_month: float | None
    min_age_years: float | None
    max_age_years: float | None
    similarity: float


class DrivingTrial(BaseModel):
    nct_id: str
    title: str | None
    detail: str


class CriterionScore(BaseModel):
    criterion_id: str
    kind: Literal["inclusion", "exclusion"]
    text: str
    category: str
    score: int = Field(ge=0, le=100)
    level: Level
    basis: Literal["range", "prevalence", "burden"]
    rationale: str
    n_compared: int
    driving_trials: list[DrivingTrial]


class BenchmarkSummary(BaseModel):
    n_similar: int
    median_enrollment: float
    median_site_count: float | None
    median_duration_months: float
    median_accrual_rate_per_site_month: float | None
    median_criteria_count: float


class Assessment(BaseModel):
    protocol_id: str
    overall_score: int
    red_flags: int
    summary: BenchmarkSummary
    criteria: list[CriterionScore]
    similar_trials: list[SimilarTrial]


class CompetingTrial(BaseModel):
    nct_id: str
    title: str | None
    phase: str
    enrollment: int | None
    sites_in_country: int


class CountryCompetition(BaseModel):
    country: str
    planned_sites: int | None
    competing_trials: int
    competing_sites: int
    crowding: Level
    trials: list[CompetingTrial]


class CompetingTrials(BaseModel):
    protocol_id: str
    indication: str
    countries: list[CountryCompetition]


class EligibilityFactor(BaseModel):
    criterion_id: str
    parameter: str
    factor: float = Field(description="Share of the benchmark eligibility window the draft still allows, 0-1")
    reference_lower: float | None
    reference_upper: float | None
    n_compared: int


class TerminationRisk(BaseModel):
    risk: float = Field(ge=0, le=1, description="Estimated probability of termination for low accrual")
    level: Level
    baseline_share: float = Field(description="Share of similar trials terminated for low accrual, smoothed")
    similar_low_accrual: int
    n_similar: int
    indication_phase_share: float = Field(description="Same share over every trial of the indication and phase")
    adjustment: float = Field(description="Forecast P50 over the similar trials' median duration, limited to 0.5-4")
    trial_ids: list[str] = Field(description="Benchmark trials terminated for low accrual behind the estimate")


class Forecast(BaseModel):
    p50_months: float
    p90_months: float
    target_enrollment: int
    sites: int
    ramp_months: float
    rate_multiplier: float = Field(description="Applied to benchmark accrual rates for narrow eligibility windows")
    eligibility_factors: list[EligibilityFactor]
    rate_source: Literal["similar_trials", "indication_phase_benchmark"]
    n_rates: int
    median_benchmark_rate: float = Field(description="Median patients per site per month of the rates drawn from")
    indication_phase_median_rate: float | None
    simulations: int
    seed: int
    termination_risk: TerminationRisk


class Change(BaseModel):
    kind: Literal["relax_criterion", "add_sites"]
    criterion_id: str | None = None
    lower: float | None = None
    upper: float | None = None
    country: str | None = None
    sites: int | None = Field(default=None, ge=1, le=500)


class Evidence(BaseModel):
    metric: str = Field(description="Name of the code path that computed the value from the dataset")
    label: str
    value: float


class Suggestion(BaseModel):
    id: str
    title: str
    rationale: str
    change: Change
    evidence: list[Evidence]
    cited_trial_ids: list[str]
    p50_months_after: float
    months_saved: float


class Suggestions(BaseModel):
    protocol_id: str
    baseline: Forecast
    suggestions: list[Suggestion]
    rejected: int = Field(description="Candidates dropped because they failed the evidence validator")


class WhatIfRequest(BaseModel):
    changes: list[Change] = Field(min_length=1, max_length=20)
    seed: int | None = None


class AppliedChange(BaseModel):
    change: Change
    summary: str


class WhatIf(BaseModel):
    protocol_id: str
    baseline: Forecast
    scenario: Forecast
    applied: list[AppliedChange]
    p50_months_saved: float
    p90_months_saved: float
    elapsed_ms: float
