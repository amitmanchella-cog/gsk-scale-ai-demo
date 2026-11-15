from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient

from pda_api.benchmark import Benchmark, load_benchmark
from pda_api.config import DEFAULT_BENCHMARK_DIR, DEFAULT_SAMPLES_DIR, Settings
from pda_api.main import create_app
from pda_api.providers.mock import MockProvider
from pda_api.schemas import ProtocolDesign

WEAK = "t2d_phase3_weak"


@pytest.fixture(scope="session")
def benchmark() -> Benchmark:
    return load_benchmark(DEFAULT_BENCHMARK_DIR)


@pytest.fixture(scope="session")
def provider() -> MockProvider:
    return MockProvider()


def sample_text(key: str) -> str:
    return (DEFAULT_SAMPLES_DIR / f"{key}.txt").read_text(encoding="utf-8")


def as_docx(text: str) -> bytes:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture(scope="session")
def weak_design(provider: MockProvider) -> ProtocolDesign:
    return provider.extract_design(sample_text(WEAK))


@pytest.fixture()
def database_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture()
def client(database_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(database_url=database_url))) as test_client:
        yield test_client


def upload(client: TestClient, key: str = WEAK) -> str:
    response = client.post("/api/protocols", files={"file": (f"{key}.txt", sample_text(key), "text/plain")})
    assert response.status_code == 201, response.text
    protocol_id: str = response.json()["id"]
    return protocol_id
