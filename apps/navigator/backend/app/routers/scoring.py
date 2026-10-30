"""Scoring rules in effect and an explain endpoint for arbitrary inputs (S2)."""

from fastapi import APIRouter, HTTPException, Query

from ..deps import get_rules
from ..models import ScoreResult, ScoringRulesModel
from ..scoring import score_hcp

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/rules", response_model=ScoringRulesModel)
def scoring_rules() -> ScoringRulesModel:
    return ScoringRulesModel(**get_rules().to_dict())


@router.get("/explain", response_model=ScoreResult)
def explain(
    segment: str = Query(..., description="HCP segment, e.g. A"),
    days_since_last_visit: int | None = Query(None, ge=0, description="Omit for an HCP that was never visited"),
    open_follow_ups: int = Query(0, ge=0),
) -> ScoreResult:
    rules = get_rules()
    if segment not in rules.segment_weights:
        raise HTTPException(
            status_code=422, detail=f"unknown segment {segment!r}; expected one of {sorted(rules.segment_weights)}"
        )
    result = score_hcp(segment, days_since_last_visit, open_follow_ups, rules)
    return ScoreResult(**result.to_dict())
