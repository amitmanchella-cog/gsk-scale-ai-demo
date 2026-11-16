from __future__ import annotations

import gzip
import importlib.util
import sys
import urllib.error
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_snapshot.py"


@pytest.fixture
def fetch_snapshot() -> Any:
    spec = importlib.util.spec_from_file_location("fetch_snapshot", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read()


def _seed_previous_snapshot(out: Path, names: list[str]) -> None:
    for name in names:
        with gzip.open(out / name, "wt", encoding="utf-8") as fh:
            fh.write("previous snapshot\n")
    (out / "MANIFEST.json").write_text("previous manifest\n")


def test_failed_refresh_keeps_the_previous_snapshot(
    fetch_snapshot: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    names = [f"{dataset}_studies.jsonl.gz" for dataset in fetch_snapshot.DATASETS]
    _seed_previous_snapshot(tmp_path, names)
    calls = 0

    def flaky_fetch(condition: str, statuses: str, limit: int) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        if calls > 3:  # the reachability probe and two indications succeed, then the API drops
            raise urllib.error.URLError("connection reset")
        return [{"protocolSection": {"identificationModule": {"nctId": f"NCT{calls:08d}"}}}]

    monkeypatch.setattr(fetch_snapshot, "fetch", flaky_fetch)
    monkeypatch.setattr(sys, "argv", ["fetch_snapshot.py", "--out", str(tmp_path)])
    with pytest.raises(urllib.error.URLError):
        fetch_snapshot.main()

    for name in names:
        assert _read(tmp_path / name) == "previous snapshot\n"
    assert (tmp_path / "MANIFEST.json").read_text() == "previous manifest\n"


def test_successful_refresh_replaces_the_snapshot(
    fetch_snapshot: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    names = [f"{dataset}_studies.jsonl.gz" for dataset in fetch_snapshot.DATASETS]
    _seed_previous_snapshot(tmp_path, names)
    study = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}
    monkeypatch.setattr(fetch_snapshot, "fetch", lambda condition, statuses, limit: [study])
    monkeypatch.setattr(sys, "argv", ["fetch_snapshot.py", "--out", str(tmp_path)])
    fetch_snapshot.main()

    for name in names:
        assert "NCT00000001" in _read(tmp_path / name)
    assert not list(tmp_path.glob("*.partial"))
    assert "previous" not in (tmp_path / "MANIFEST.json").read_text()
