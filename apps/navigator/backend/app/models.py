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
