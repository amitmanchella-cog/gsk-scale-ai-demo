"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pda_api import __version__
from pda_api.benchmark import load_benchmark
from pda_api.config import Settings
from pda_api.db import create_schema, make_engine, make_session_factory
from pda_api.routers import assessment, protocols


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        await create_schema(engine)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        load_benchmark(settings.benchmark_dir)
        yield
        await engine.dispose()

    app = FastAPI(
        title="Protocol Design Advisor API",
        version=__version__,
        description="Benchmarks a draft clinical-trial protocol against public ClinicalTrials.gov data.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict[str, object]:
        benchmark = load_benchmark(settings.benchmark_dir)
        return {
            "status": "ok",
            "version": __version__,
            "llm_provider": settings.llm_provider,
            "benchmark_trials": len(benchmark.trials),
        }

    for router in (protocols.router, assessment.router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
