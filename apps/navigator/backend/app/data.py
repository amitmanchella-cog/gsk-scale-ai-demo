"""Load the curated UC1 tables (``data/*.parquet``) into memory.

The data directory defaults to ``<repo root>/data`` (resolved relative to this file, never the CWD) and can be
overridden with the ``NAVIGATOR_DATA_DIR`` environment variable.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

TABLES = ("hcps", "visits", "follow_ups", "reps", "territories", "weekly_sales")

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DATA_DIR_ENV = "NAVIGATOR_DATA_DIR"


def resolve_data_dir(override: str | os.PathLike | None = None) -> Path:
    """Return the data directory: explicit argument > ``NAVIGATOR_DATA_DIR`` > ``<repo root>/data``."""
    raw = override if override is not None else os.environ.get(DATA_DIR_ENV)
    if raw is None or str(raw) == "":
        return DEFAULT_DATA_DIR
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


@dataclass
class DataStore:
    """In-memory copy of the curated tables, keyed by table name."""

    data_dir: Path
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)

    def __getitem__(self, name: str) -> pd.DataFrame:
        return self.tables[name]

    @property
    def row_counts(self) -> dict[str, int]:
        return {name: int(len(df)) for name, df in self.tables.items()}


def load_tables(data_dir: str | os.PathLike | None = None) -> DataStore:
    """Read every table in :data:`TABLES` from ``data_dir`` with pandas + pyarrow."""
    directory = resolve_data_dir(data_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"navigator data directory not found: {directory}")
    store = DataStore(data_dir=directory)
    for name in TABLES:
        path = directory / f"{name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"missing curated table {name!r}: {path}")
        store.tables[name] = pd.read_parquet(path, engine="pyarrow")
    return store
