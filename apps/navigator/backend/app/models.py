"""Pydantic response models."""

from datetime import date

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    version: str
    data_dir: str
    as_of: date
    row_counts: dict[str, int]


class Territory(BaseModel):
    territory_id: str
    territory_name: str
    region: str


class Rep(BaseModel):
    rep_id: str
    rep_name: str
    territory_id: str
    region: str | None = None
    hire_date: date | None = None


class ScoringRulesModel(BaseModel):
    segment_weights: dict[str, int]
    points_per_day: int
    days_cap: int
    open_follow_up_bonus: int
    recent_visit_days: int
    max_score: int


class ScoreFactor(BaseModel):
    name: str
    points: int
    detail: str


class ScoreResult(BaseModel):
    score: int
    reason: str
    factors: list[ScoreFactor]


class HcpView(BaseModel):
    hcp_id: str
    hcp_name: str
    specialty: str
    segment: str
    territory_id: str
    last_visit_date: date | None
    days_since_last_visit: int | None
    open_follow_ups: int
    score: int
    reason: str
    factors: list[ScoreFactor]


class RepSummary(BaseModel):
    rep_id: str
    rep_name: str
    territory_id: str


class HcpListResponse(BaseModel):
    rep: RepSummary
    territory: Territory
    as_of: date
    count: int
    hcps: list[HcpView]
