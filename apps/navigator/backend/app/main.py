"""FastAPI application for the UC4 Field Force Navigator."""

import os
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.data import DataStore, load_tables
from app.models import Health, Rep, Territory

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def cors_origins() -> list[str]:
    raw = os.environ.get("NAVIGATOR_CORS_ORIGINS")
    if not raw:
        return DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = load_tables()
    yield
    app.state.store = None


app = FastAPI(title="Field Force Navigator API", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_store() -> DataStore:
    store = getattr(app.state, "store", None)
    if store is None:
        store = app.state.store = load_tables()
    return store


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


@app.get("/health", response_model=Health)
def health() -> Health:
    store = get_store()
    return Health(status="ok", version=__version__, data_dir=str(store.data_dir), row_counts=store.row_counts)


@app.get("/territories", response_model=list[Territory])
def list_territories() -> list[Territory]:
    territories = get_store()["territories"].sort_values("territory_id")
    return [Territory(**row) for row in _records(territories)]


@app.get("/reps", response_model=list[Rep])
def list_reps() -> list[Rep]:
    store = get_store()
    reps = store["reps"].merge(store["territories"][["territory_id", "region"]], on="territory_id", how="left")
    reps = reps.sort_values("rep_id")
    return [Rep(**row) for row in _records(reps)]
