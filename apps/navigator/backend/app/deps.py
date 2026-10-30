"""Request-time access to the shared in-memory state (DataStore, scoring rules)."""

from .data import DataStore, load_tables
from .scoring import ScoringRules, load_rules

_state: dict[str, DataStore | ScoringRules | None] = {"store": None, "rules": None}


def set_store(store: DataStore | None) -> None:
    _state["store"] = store


def get_store() -> DataStore:
    store = _state["store"]
    if store is None:
        store = load_tables()
        _state["store"] = store
    return store


def set_rules(rules: ScoringRules | None) -> None:
    _state["rules"] = rules


def get_rules() -> ScoringRules:
    """Scoring rules in effect, loaded once from the environment (see ``scoring.load_rules``)."""
    rules = _state["rules"]
    if rules is None:
        rules = load_rules()
        _state["rules"] = rules
    return rules
