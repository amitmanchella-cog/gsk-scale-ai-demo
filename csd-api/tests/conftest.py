from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from csd_api.app import create_app


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'csd-test.db'}"


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    with TestClient(create_app(database_url)) as test_client:
        yield test_client


@pytest.fixture
def root_id(client: TestClient) -> str:
    return str(client.get("/studies/asthma-ref").json()["root_version_id"])
