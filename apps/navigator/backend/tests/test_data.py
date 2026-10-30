from pathlib import Path

import pytest
from app import data


def test_default_data_dir_is_repo_root_data(monkeypatch):
    monkeypatch.delenv(data.DATA_DIR_ENV, raising=False)
    assert data.resolve_data_dir() == data.REPO_ROOT / "data"
    assert (data.REPO_ROOT / "pyproject.toml").is_file()


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(data.DATA_DIR_ENV, str(tmp_path))
    assert data.resolve_data_dir() == tmp_path


def test_relative_override_resolves_against_repo_root(monkeypatch):
    monkeypatch.setenv(data.DATA_DIR_ENV, "data")
    assert data.resolve_data_dir() == (data.REPO_ROOT / "data").resolve()


def test_load_tables_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        data.load_tables(tmp_path / "nope")


def test_load_tables_reads_all_tables():
    store = data.load_tables()
    assert set(store.tables) == set(data.TABLES)
    assert isinstance(store.data_dir, Path)
    assert store.row_counts["hcps"] == 1600
