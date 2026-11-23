"""Design-review report export."""

from __future__ import annotations

from datetime import UTC
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool

from pda_api.deps import BenchmarkDep, DesignDep, RecordDep, similar_trials
from pda_api.forecast import ForecastError
from pda_api.report import build_report, render_html, render_pdf
from pda_api.schemas import Report
from pda_api.similarity import DEFAULT_SIMILAR
from pda_api.suggestions import ChangeError, Context

router = APIRouter(tags=["report"])


@router.get(
    "/protocols/{protocol_id}/report",
    response_model=Report,
    responses={200: {"content": {"text/html": {}, "application/pdf": {}}}},
)
async def get_report(
    record: RecordDep,
    design: DesignDep,
    benchmark: BenchmarkDep,
    format: Annotated[Literal["html", "pdf", "json"], Query()] = "html",
    accept: Annotated[list[str] | None, Query(description="ID of an accepted suggestion; repeat per change")] = None,
) -> Response | Report:
    """The design, scores, forecast, accepted changes and cited trials, as HTML, PDF or JSON."""
    ranked = similar_trials(design, benchmark, DEFAULT_SIMILAR)
    context = Context(design=design, similar=[trial for trial, _ in ranked], benchmark=benchmark)
    try:
        # SQLite drops the time zone; stored values are always UTC.
        created_at = record.created_at.replace(tzinfo=UTC)
        # The simulations and the page layout are CPU-bound, so they run off the event loop.
        report = await run_in_threadpool(build_report, record.id, record.document, created_at, context, ranked, accept)
    except (ChangeError, ForecastError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if format == "json":
        return report
    filename = f"design-review-{record.id[:8]}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if format == "pdf":
        return Response(await run_in_threadpool(render_pdf, report), media_type="application/pdf", headers=headers)
    return Response(
        await run_in_threadpool(render_html, report), media_type="text/html; charset=utf-8", headers=headers
    )
