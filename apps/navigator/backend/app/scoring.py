"""Visit priority score (S2) — a pure, dependency-free module.

``score_hcp`` turns (segment, days since last visit, open follow-ups) into a 0–100 score with a plain-language
reason. The rules are loaded once by ``load_rules`` from ``NAVIGATOR_SCORING_RULES`` (JSON object with any subset
of the fields) > ``NAVIGATOR_SCORING_RULES_FILE`` > the defaults below.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

RULES_ENV = "NAVIGATOR_SCORING_RULES"
RULES_FILE_ENV = "NAVIGATOR_SCORING_RULES_FILE"
REQUIRED_SEGMENTS = ("A", "B", "C")
DEFAULT_SEGMENT_WEIGHTS = {"A": 40, "B": 25, "C": 10}


@dataclass(frozen=True)
class ScoringRules:
    segment_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_SEGMENT_WEIGHTS))
    points_per_day: int = 1
    days_cap: int = 40
    open_follow_up_bonus: int = 20
    recent_visit_days: int = 7
    max_score: int = 100

    def __post_init__(self) -> None:
        if not isinstance(self.segment_weights, Mapping):
            raise ValueError("segment_weights must be an object mapping segment -> weight")
        missing = [seg for seg in REQUIRED_SEGMENTS if seg not in self.segment_weights]
        if missing:
            raise ValueError(f"segment_weights must define weights for {', '.join(missing)}")
        for segment, weight in self.segment_weights.items():
            _check_non_negative_int(f"segment_weights[{segment!r}]", weight)
        for name in ("points_per_day", "days_cap", "open_follow_up_bonus", "recent_visit_days", "max_score"):
            _check_non_negative_int(name, getattr(self, name))
        object.__setattr__(self, "segment_weights", dict(self.segment_weights))

    def to_dict(self) -> dict:
        return asdict(self)


def _check_non_negative_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")


DEFAULT_RULES = ScoringRules()


@dataclass(frozen=True)
class ScoreFactor:
    name: str
    points: int
    detail: str


@dataclass(frozen=True)
class ScoreResult:
    score: int
    reason: str
    factors: list[ScoreFactor]

    def to_dict(self) -> dict:
        return asdict(self)


def _plural(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def score_hcp(
    segment: str,
    days_since_last_visit: int | None,
    open_follow_ups: int,
    rules: ScoringRules = DEFAULT_RULES,
) -> ScoreResult:
    """Score one HCP. ``days_since_last_visit=None`` means never visited."""
    if segment not in rules.segment_weights:
        raise ValueError(f"unknown segment {segment!r}; expected one of {sorted(rules.segment_weights)}")
    if days_since_last_visit is not None and days_since_last_visit <= rules.recent_visit_days:
        detail = f"Visited {days_since_last_visit} days ago (within {rules.recent_visit_days} days)"
        return ScoreResult(score=0, reason=detail, factors=[ScoreFactor("recent_visit", 0, detail)])

    factors: list[ScoreFactor] = []
    parts: list[str] = []

    weight = rules.segment_weights[segment]
    factors.append(ScoreFactor("segment", weight, f"Segment {segment}"))
    parts.append(f"Segment {segment} (+{weight})")

    if days_since_last_visit is None:
        factors.append(ScoreFactor("days_since_last_visit", rules.days_cap, "never visited (capped)"))
        parts.append(f"never visited (+{rules.days_cap}, capped)")
    else:
        raw_days = days_since_last_visit * rules.points_per_day
        points = min(raw_days, rules.days_cap)
        capped = raw_days > rules.days_cap
        base = f"{days_since_last_visit} days since last visit"
        factors.append(ScoreFactor("days_since_last_visit", points, base + (" (capped)" if capped else "")))
        parts.append(f"{base} (+{points}{', capped' if capped else ''})")

    if open_follow_ups >= 1:
        detail = f"{open_follow_ups} open {_plural(open_follow_ups, 'follow-up', 'follow-ups')}"
        factors.append(ScoreFactor("open_follow_up", rules.open_follow_up_bonus, detail))
        parts.append(f"{detail} (+{rules.open_follow_up_bonus})")

    raw = sum(factor.points for factor in factors)
    score = min(raw, rules.max_score)
    reason = ", ".join(parts)
    if raw > rules.max_score:
        reason += f" → capped at {rules.max_score}"
    return ScoreResult(score=score, reason=reason, factors=factors)


def rules_from_dict(overrides: Mapping) -> ScoringRules:
    """Build rules from a JSON-like object holding any subset of the fields (unknown keys are rejected)."""
    if not isinstance(overrides, Mapping):
        raise ValueError("scoring rules must be a JSON object")
    unknown = sorted(set(overrides) - set(DEFAULT_RULES.to_dict()))
    if unknown:
        raise ValueError(f"unknown scoring rule(s): {', '.join(unknown)}")
    return ScoringRules(**{**DEFAULT_RULES.to_dict(), **overrides})


def load_rules(env: Mapping[str, str] = os.environ) -> ScoringRules:
    """``NAVIGATOR_SCORING_RULES`` (JSON) > ``NAVIGATOR_SCORING_RULES_FILE`` > defaults. Invalid -> ValueError."""
    raw = env.get(RULES_ENV)
    source = RULES_ENV
    if not raw:
        path = env.get(RULES_FILE_ENV)
        if not path:
            return DEFAULT_RULES
        source = path
        try:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
        except OSError as exc:
            raise ValueError(f"cannot read scoring rules file {path}: {exc}") from exc
    try:
        overrides = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} is not valid JSON: {exc}") from exc
    return rules_from_dict(overrides)
