"""FastAPI application: operations and queries over the csd-core service."""

from __future__ import annotations

import os
import threading
import uuid
from typing import Annotated, Any

from csd_core.application.study_service import NotHeadError, StudyService
from csd_core.domain.compare import Comparison
from csd_core.domain.drafting import Draft, DraftSection, SectionNumber
from csd_core.domain.operations import Operation, OperationError, operation_types
from csd_core.domain.schedule import ScheduleGrid, schedule_grid
from csd_core.domain.scoring import Score
from csd_core.domain.versioning import MAIN_BRANCH, Branch, Version
from csd_core.ports.version_store import NotFoundError
from csd_core.reference.asthma import REFERENCE_STUDY_ID, reference_study
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from csd_api.schemas import (
    CreateBranch,
    CreateStudy,
    FindingsOut,
    Health,
    Problem,
    StudySummary,
    VersionSummary,
)
from csd_api.sql_store import SqlVersionStore, make_engine

DEFAULT_DATABASE_URL = "sqlite:///./csd.db"

NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": Problem}}
CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem}}
REJECTED: dict[int | str, dict[str, Any]] = {
    **NOT_FOUND,
    **CONFLICT,
    422: {"model": Problem},
}


def get_service(request: Request) -> StudyService:
    service: StudyService = request.app.state.service
    return service


Service = Annotated[StudyService, Depends(get_service)]


def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.environ.get("CSD_DATABASE_URL", DEFAULT_DATABASE_URL)
    service = StudyService(SqlVersionStore(make_engine(url)))
    # One writer at a time: applying an operation reads the head and then moves it.
    write_lock = threading.Lock()
    with write_lock:
        if REFERENCE_STUDY_ID not in service.list_study_ids():
            service.create_study(REFERENCE_STUDY_ID, reference_study())

    app = FastAPI(
        title="csd-api",
        version="0.1.0",
        description="Computable study design core API. Synthetic data only.",
    )
    app.state.service = service

    @app.exception_handler(NotFoundError)
    def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(NotHeadError)
    def not_head(_: Request, error: NotHeadError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(OperationError)
    def rejected(_: Request, error: OperationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.get("/health")
    def health(service: Service) -> Health:
        return Health(status="ok", studies=len(service.list_study_ids()))

    @app.get("/operation-types")
    def list_operation_types() -> list[str]:
        return list(operation_types())

    # --- studies ------------------------------------------------------------------

    def summarise(service: StudyService, study_id: str) -> StudySummary:
        versions = service.list_versions(study_id)
        return StudySummary(
            id=study_id,
            title=versions[0].graph.title,
            root_version_id=versions[0].id,
            head_version_id=service.head(study_id, MAIN_BRANCH).id,
            version_count=len(versions),
        )

    @app.get("/studies")
    def list_studies(service: Service) -> list[StudySummary]:
        return [summarise(service, study_id) for study_id in service.list_study_ids()]

    @app.post("/studies", status_code=201, responses=CONFLICT)
    def create_study(
        service: Service, body: Annotated[CreateStudy | None, Body()] = None
    ) -> StudySummary:
        """Create a new study from the synthetic reference study (a clean sandbox)."""
        study_id = (body.id if body else None) or f"study-{uuid.uuid4().hex[:10]}"
        with write_lock:
            if study_id in service.list_study_ids():
                raise HTTPException(status_code=409, detail=f"study {study_id!r} already exists")
            service.create_study(study_id, reference_study())
        return summarise(service, study_id)

    @app.get("/studies/{study_id}", responses=NOT_FOUND)
    def get_study(study_id: str, service: Service) -> StudySummary:
        return summarise(service, study_id)

    @app.get("/studies/{study_id}/versions", responses=NOT_FOUND)
    def list_versions(study_id: str, service: Service) -> list[VersionSummary]:
        return [VersionSummary.of(version) for version in service.list_versions(study_id)]

    @app.get("/studies/{study_id}/branches", responses=NOT_FOUND)
    def list_branches(study_id: str, service: Service) -> list[Branch]:
        return service.list_branches(study_id)

    # --- versions -----------------------------------------------------------------

    @app.get("/versions/{version_id}", responses=NOT_FOUND)
    def get_version(version_id: str, service: Service) -> Version:
        return service.get_version(version_id)

    @app.post("/versions/{version_id}/operations", status_code=201, responses=REJECTED)
    def apply_operation(
        version_id: str,
        operation: Operation,
        service: Service,
        branch: Annotated[
            str | None,
            Query(description="Branch to extend. Defaults to the version's own branch."),
        ] = None,
    ) -> Version:
        """Apply a typed operation to a branch head and return the new version."""
        with write_lock:
            return service.apply(version_id, operation, branch=branch)

    @app.post("/versions/{version_id}/branches", status_code=201, responses=REJECTED)
    def create_branch(version_id: str, body: CreateBranch, service: Service) -> Branch:
        """Start a branch from any version. Its head is that version until an operation
        is posted to it with ``?branch=<name>``."""
        with write_lock:
            return service.create_branch(version_id, body.name)

    @app.get("/versions/{version_id}/score", responses=NOT_FOUND)
    def get_score(version_id: str, service: Service) -> Score:
        return service.score(version_id)

    @app.get("/versions/{version_id}/findings", responses=NOT_FOUND)
    def get_findings(version_id: str, service: Service) -> FindingsOut:
        version = service.get_version(version_id)
        return FindingsOut(
            version_id=version.id, count=len(version.findings), findings=version.findings
        )

    @app.get("/versions/{version_id}/schedule", responses=NOT_FOUND)
    def get_schedule(version_id: str, service: Service) -> ScheduleGrid:
        return schedule_grid(service.get_version(version_id).graph)

    # --- M11 drafts ---------------------------------------------------------------

    @app.get("/versions/{version_id}/drafts", responses=NOT_FOUND)
    def get_drafts(version_id: str, service: Service) -> Draft:
        """ICH M11 sections 3, 5 and 8 drafted from this version's graph.

        Every sentence lists the IDs of the graph elements it was written from.
        """
        return service.draft(version_id)

    @app.get("/versions/{version_id}/drafts/{section}", responses=NOT_FOUND)
    def get_draft_section(
        version_id: str, section: SectionNumber, service: Service
    ) -> DraftSection:
        """One drafted M11 section: 3, 5 or 8."""
        return service.draft(version_id, (section,)).sections[0]

    # --- compare ------------------------------------------------------------------

    @app.get("/compare", responses={**NOT_FOUND, 422: {"model": Problem}})
    def compare(
        service: Service,
        left: Annotated[str, Query(description="Version ID shown on the left")],
        right: Annotated[str, Query(description="Version ID shown on the right")],
    ) -> Comparison:
        """Two versions side by side: scores, findings, delta (right minus left) and changes."""
        return service.compare(left, right)

    return app
