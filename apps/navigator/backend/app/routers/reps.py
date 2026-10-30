"""Reps and territories (scaffold endpoints, moved out of main.py)."""

import pandas as pd
from fastapi import APIRouter

from ..deps import get_store
from ..models import Rep, Territory

router = APIRouter(tags=["reps"])


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of dicts with NaN/NaT turned into None (safe for pydantic)."""
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


@router.get("/territories", response_model=list[Territory])
def list_territories() -> list[Territory]:
    territories = get_store()["territories"].sort_values("territory_id")
    return [Territory(**row) for row in records(territories)]


@router.get("/reps", response_model=list[Rep])
def list_reps() -> list[Rep]:
    store = get_store()
    reps = store["reps"].merge(store["territories"][["territory_id", "region"]], on="territory_id", how="left")
    reps = reps.sort_values("rep_id")
    return [Rep(**row) for row in records(reps)]
