"""Runtime settings, read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_DIR = PACKAGE_ROOT / "tests" / "fixtures" / "benchmark" / "v1"
DEFAULT_SAMPLES_DIR = PACKAGE_ROOT / "samples"


def _origins() -> list[str]:
    raw = os.environ.get("PDA_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    # SQLite for the demo; set e.g. postgresql+asyncpg://user:pass@host/db for PostgreSQL.
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./pda.db"))
    benchmark_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("PDA_BENCHMARK_DIR", str(DEFAULT_BENCHMARK_DIR)))
    )
    samples_dir: Path = field(default_factory=lambda: Path(os.environ.get("PDA_SAMPLES_DIR", str(DEFAULT_SAMPLES_DIR))))
    llm_provider: str = field(default_factory=lambda: os.environ.get("PDA_LLM_PROVIDER", "mock"))
    cors_origins: list[str] = field(default_factory=_origins)
    max_upload_bytes: int = 2_000_000
