"""Enrollment forecast, suggestions and what-if."""

from __future__ import annotations

from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from pda_api.deps import BenchmarkDep, DesignDep, RecordDep, similar_trials
from pda_api.forecast import DEFAULT_SEED, ForecastError
from pda_api.schemas import Forecast, Suggestions, WhatIf, WhatIfRequest
from pda_api.similarity import DEFAULT_SIMILAR
from pda_api.suggestions import ChangeError, Context, applied, suggest

router = APIRouter(tags=["forecast"])

SeedQuery = Annotated[int, Query(ge=0, description="Seed of the simulation; the same seed gives the same forecast")]


def get_context(design: DesignDep, benchmark: BenchmarkDep) -> Context:
    similar = [trial for trial, _ in similar_trials(design, benchmark, DEFAULT_SIMILAR)]
    return Context(design=design, similar=similar, benchmark=benchmark)


ContextDep = Annotated[Context, Depends(get_context)]


def _baseline(context: Context) -> Forecast:
    try:
        return context.baseline
    except ForecastError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/protocols/{protocol_id}/forecast", response_model=Forecast)
async def get_forecast(context: ContextDep, seed: SeedQuery = DEFAULT_SEED) -> Forecast:
    """P50 and P90 months to full enrollment and the risk of termination for low accrual."""
    context.seed = seed
    return _baseline(context)


@router.get("/protocols/{protocol_id}/suggestions", response_model=Suggestions)
async def get_suggestions(record: RecordDep, context: ContextDep, seed: SeedQuery = DEFAULT_SEED) -> Suggestions:
    """Design changes that shorten the forecast. Each one passed the evidence validator."""
    context.seed = seed
    baseline = _baseline(context)
    suggestions, rejected = suggest(context)
    return Suggestions(protocol_id=record.id, baseline=baseline, suggestions=suggestions, rejected=rejected)


@router.post("/protocols/{protocol_id}/what-if", response_model=WhatIf)
async def what_if(record: RecordDep, context: ContextDep, body: WhatIfRequest) -> WhatIf:
    """Apply the chosen changes and recompute the forecast against the same benchmark and seed."""
    started = perf_counter()
    context.seed = body.seed if body.seed is not None else DEFAULT_SEED
    baseline = _baseline(context)
    try:
        scenario = context.scenario(body.changes)
        summaries = applied(context.design, body.changes)
    except (ChangeError, ForecastError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return WhatIf(
        protocol_id=record.id,
        baseline=baseline,
        scenario=scenario,
        applied=summaries,
        p50_months_saved=round(baseline.p50_months - scenario.p50_months, 1),
        p90_months_saved=round(baseline.p90_months - scenario.p90_months, 1),
        elapsed_ms=round(1000 * (perf_counter() - started), 1),
    )
