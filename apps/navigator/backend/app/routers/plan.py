"""Weekly plan endpoints (S3): ``/reps/{rep_id}/plan…``. S4 adds ``GET …/plan/export.csv`` here."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from ..deps import get_rules, get_store
from ..plans import AddVisitRequest, Plan, PlanError, add_visit, build_plan, clear_plan, remove_visit

router = APIRouter(prefix="/reps/{rep_id}/plan", tags=["plan"])

AS_OF_QUERY = Query(None, description="Override the as-of date (YYYY-MM-DD); defaults to the data's as-of date")


def _http(error: PlanError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("", response_model=Plan)
def get_plan(rep_id: str, as_of: date | None = AS_OF_QUERY) -> Plan:
    try:
        return build_plan(get_store(), rep_id, as_of, get_rules())
    except PlanError as error:
        raise _http(error) from error


@router.post("/visits", response_model=Plan, status_code=status.HTTP_201_CREATED)
def post_visit(rep_id: str, body: AddVisitRequest, as_of: date | None = AS_OF_QUERY) -> Plan:
    try:
        return add_visit(get_store(), rep_id, body.hcp_id, body.day, as_of)
    except PlanError as error:
        raise _http(error) from error


@router.delete("/visits/{visit_id}", response_model=Plan)
def delete_visit(rep_id: str, visit_id: int, as_of: date | None = AS_OF_QUERY) -> Plan:
    try:
        return remove_visit(get_store(), rep_id, visit_id, as_of)
    except PlanError as error:
        raise _http(error) from error


@router.delete("", response_model=Plan)
def delete_plan(rep_id: str, as_of: date | None = AS_OF_QUERY) -> Plan:
    try:
        return clear_plan(get_store(), rep_id, as_of)
    except PlanError as error:
        raise _http(error) from error
