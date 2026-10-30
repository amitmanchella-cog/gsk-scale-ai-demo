"""FastAPI application for the UC4 Field Force Navigator."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .data import DataStore, load_tables
from .deps import get_store, set_store
from .models import Health
from .routers import reps

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def cors_origins() -> list[str]:
    raw = os.environ.get("NAVIGATOR_CORS_ORIGINS")
    if not raw:
        return DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_store(load_tables())
    yield
    set_store(None)


app = FastAPI(title="Field Force Navigator API", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(reps.router)


@app.get("/health", response_model=Health)
def health() -> Health:
    store: DataStore = get_store()
    return Health(
        status="ok",
        version=__version__,
        data_dir=str(store.data_dir),
        as_of=store.as_of,
        row_counts=store.row_counts,
    )
