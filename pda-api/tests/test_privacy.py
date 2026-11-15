"""Fail if anything person-level reaches the database schema or its rows."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.conftest import upload

from pda_api.db import Base

PERSON_COLUMN = re.compile(
    r"(^|_)(name|first|last|surname|email|e_mail|phone|address|dob|birth|birthdate|patient|subject|participant|"
    r"mrn|ssn|nhs|investigator|contact)(_|$)"
)
PERSON_VALUE = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "date of birth": re.compile(r"\b(?:dob|date of birth|born on)\b", re.IGNORECASE),
    "patient id": re.compile(
        r"\b(?:patient|subject|participant)[\s_-]*(?:id|no|number)\b\s*[:#]?\s*\w+", re.IGNORECASE
    ),
    "phone": re.compile(r"\+?\d{1,3}[\s-]\(?\d{2,4}\)?[\s-]\d{3,4}[\s-]\d{3,4}"),
}


def person_columns(columns: list[str]) -> list[str]:
    return [column for column in columns if PERSON_COLUMN.search(column.lower())]


def person_values(value: Any) -> list[str]:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return [label for label, pattern in PERSON_VALUE.items() if pattern.search(text)]


def scan(database: Path) -> list[str]:
    findings: list[str] = []
    with sqlite3.connect(database) as conn:
        tables = [row[0] for row in conn.execute("select name from sqlite_master where type='table'")]
        for table in tables:
            columns = [row[1] for row in conn.execute(f"pragma table_info({table})")]
            findings += [f"{table}.{column}: person-level column" for column in person_columns(columns)]
            for row in conn.execute(f"select * from {table}"):  # noqa: S608 - table names come from sqlite_master
                for column, value in zip(columns, row, strict=True):
                    findings += [f"{table}.{column}: {label} in stored value" for label in person_values(value)]
    return findings


def test_declared_schema_has_no_person_level_columns() -> None:
    columns = [f"{table.name}.{column.name}" for table in Base.metadata.tables.values() for column in table.columns]
    assert columns, "no tables declared"
    assert person_columns([column.split(".")[1] for column in columns]) == []


def test_database_after_use_has_no_person_level_data(client: TestClient, tmp_path: Path) -> None:
    for key in ("t2d_phase3_weak", "asthma_phase3", "copd_phase2"):
        protocol_id = upload(client, key)
        client.get(f"/api/protocols/{protocol_id}/assessment")
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as conn:
        assert conn.execute("select count(*) from protocols").fetchone()[0] == 3
    assert scan(database) == []


def test_document_text_is_not_stored(client: TestClient, tmp_path: Path) -> None:
    upload(client)
    with sqlite3.connect(tmp_path / "test.db") as conn:
        stored = json.dumps(conn.execute("select * from protocols").fetchall(), default=str)
    assert "BACKGROUND AND RATIONALE" not in stored and "fictional once-weekly" not in stored


@pytest.mark.parametrize(
    ("column", "value", "expected"),
    [
        ("patient_id", "x", "person-level column"),
        ("investigator_name", "x", "person-level column"),
        ("date_of_birth", "x", "person-level column"),
        ("note", "reach me at jane.doe@example.org", "email"),
        ("note", "DOB 1980-02-03", "date of birth"),
        ("note", "Patient ID: 00123", "patient id"),
    ],
)
def test_scanner_catches_planted_person_level_data(tmp_path: Path, column: str, value: str, expected: str) -> None:
    database = tmp_path / "planted.db"
    with sqlite3.connect(database) as conn:
        conn.execute(f"create table planted ({column} text)")
        conn.execute("insert into planted values (?)", (value,))
    assert any(expected in finding for finding in scan(database))
