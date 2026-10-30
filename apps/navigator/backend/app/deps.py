"""Request-time access to the shared in-memory state (DataStore)."""

from .data import DataStore, load_tables

_state: dict[str, DataStore | None] = {"store": None}


def set_store(store: DataStore | None) -> None:
    _state["store"] = store


def get_store() -> DataStore:
    store = _state["store"]
    if store is None:
        store = load_tables()
        _state["store"] = store
    return store
