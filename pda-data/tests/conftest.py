from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pyspark.sql import DataFrame, SparkSession

from pda_data.job import get_spark, read_raw

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    session = get_spark("pda-data-tests")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def raw(spark: SparkSession) -> DataFrame:
    return read_raw(spark, FIXTURES / "studies.jsonl")
