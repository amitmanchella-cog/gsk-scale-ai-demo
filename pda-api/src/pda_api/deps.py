"""FastAPI dependencies shared by the routers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from pda_api.benchmark import Benchmark, Trial, load_benchmark
from pda_api.config import Settings
from pda_api.db import ProtocolRecord
from pda_api.providers import LLMProvider, get_provider
from pda_api.schemas import ProtocolDesign
from pda_api.similarity import find_similar


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_benchmark(settings: Annotated[Settings, Depends(get_settings)]) -> Benchmark:
    return load_benchmark(settings.benchmark_dir)


def get_llm(settings: Annotated[Settings, Depends(get_settings)]) -> LLMProvider:
    return get_provider(settings.llm_provider)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
BenchmarkDep = Annotated[Benchmark, Depends(get_benchmark)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ProviderDep = Annotated[LLMProvider, Depends(get_llm)]


async def load_record(protocol_id: str, session: SessionDep) -> ProtocolRecord:
    record = await session.get(ProtocolRecord, protocol_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return record


RecordDep = Annotated[ProtocolRecord, Depends(load_record)]


def load_design(record: RecordDep) -> ProtocolDesign:
    return ProtocolDesign.model_validate(record.design)


DesignDep = Annotated[ProtocolDesign, Depends(load_design)]


def similar_trials(design: ProtocolDesign, benchmark: Benchmark, limit: int) -> list[tuple[Trial, float]]:
    return find_similar(design, benchmark.trials, limit)
