"""Similar trials, restrictiveness scores and competing trials."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from pda_api.competing import competing_by_country
from pda_api.deps import BenchmarkDep, DesignDep, RecordDep, similar_trials
from pda_api.restrictiveness import HIGH, score_design, summarise
from pda_api.schemas import Assessment, CompetingTrials
from pda_api.similarity import DEFAULT_SIMILAR, MAX_SIMILAR, MIN_SIMILAR, to_schema

router = APIRouter(tags=["assessment"])


@router.get("/protocols/{protocol_id}/assessment", response_model=Assessment)
async def assess(
    record: RecordDep,
    design: DesignDep,
    benchmark: BenchmarkDep,
    similar: Annotated[int, Query(ge=MIN_SIMILAR, le=MAX_SIMILAR)] = DEFAULT_SIMILAR,
) -> Assessment:
    """The most similar benchmark trials and a 0-100 restrictiveness score per criterion."""
    ranked = similar_trials(design, benchmark, similar)
    trials = [trial for trial, _ in ranked]
    scores = score_design(design, trials)
    return Assessment(
        protocol_id=record.id,
        overall_score=round(sum(score.score for score in scores) / len(scores)) if scores else 0,
        red_flags=sum(1 for score in scores if score.score >= HIGH),
        summary=summarise(trials),
        criteria=scores,
        similar_trials=[to_schema(trial, similarity) for trial, similarity in ranked],
    )


@router.get("/protocols/{protocol_id}/competing-trials", response_model=CompetingTrials)
async def competing_trials(record: RecordDep, design: DesignDep, benchmark: BenchmarkDep) -> CompetingTrials:
    """Recruiting trials of the same indication in each planned country."""
    return CompetingTrials(
        protocol_id=record.id,
        indication=record.indication,
        countries=competing_by_country(design, benchmark.recruiting),
    )
