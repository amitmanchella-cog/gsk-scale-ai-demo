"""S2 scoring unit tests (AC2, AC3, S2.1–S2.3 and boundaries) — pure literals, no data."""

import json

import pytest
from navigator_app.scoring import (
    DEFAULT_RULES,
    ScoreFactor,
    ScoringRules,
    load_rules,
    rules_from_dict,
    score_hcp,
)


def factor_names(result):
    return [factor.name for factor in result.factors]


def test_ac2_segment_a_45_days_open_follow_up():
    result = score_hcp("A", 45, 1)
    assert result.score == 100
    assert result.reason == "Segment A (+40), 45 days since last visit (+40, capped), 1 open follow-up (+20)"
    assert result.factors == [
        ScoreFactor("segment", 40, "Segment A"),
        ScoreFactor("days_since_last_visit", 40, "45 days since last visit (capped)"),
        ScoreFactor("open_follow_up", 20, "1 open follow-up"),
    ]


def test_ac3_visited_3_days_ago_scores_zero():
    for segment, open_follow_ups in (("A", 0), ("B", 2), ("C", 5)):
        result = score_hcp(segment, 3, open_follow_ups)
        assert result.score == 0
        assert result.reason == "Visited 3 days ago (within 7 days)"
        assert result.factors == [ScoreFactor("recent_visit", 0, "Visited 3 days ago (within 7 days)")]


def test_never_visited_counts_as_cap():
    result = score_hcp("B", None, 0)
    assert result.score == 65
    assert result.reason == "Segment B (+25), never visited (+40, capped)"
    assert factor_names(result) == ["segment", "days_since_last_visit"]
    assert result.factors[1].points == 40
    assert "never visited" in result.factors[1].detail


def test_segment_c_12_days():
    result = score_hcp("C", 12, 0)
    assert result.score == 22
    assert result.reason == "Segment C (+10), 12 days since last visit (+12)"
    assert len(result.factors) == 2
    assert "+0" not in result.reason


def test_rules_from_env():
    env = {"NAVIGATOR_SCORING_RULES": json.dumps({"segment_weights": {"A": 50, "B": 25, "C": 10}})}
    rules = load_rules(env)
    assert rules.segment_weights == {"A": 50, "B": 25, "C": 10}
    assert rules.days_cap == 40  # untouched fields keep their defaults
    result = score_hcp("A", 10, 0, rules)
    assert result.score == 60
    assert result.reason == "Segment A (+50), 10 days since last visit (+10)"


def test_rules_from_file(tmp_path):
    path = tmp_path / "scoring_rules.json"
    path.write_text(json.dumps({"open_follow_up_bonus": 30, "recent_visit_days": 3}), encoding="utf-8")
    rules = load_rules({"NAVIGATOR_SCORING_RULES_FILE": str(path)})
    assert rules.open_follow_up_bonus == 30
    assert rules.recent_visit_days == 3
    assert score_hcp("C", 5, 1, rules).reason == "Segment C (+10), 5 days since last visit (+5), 1 open follow-up (+30)"


def test_env_json_wins_over_file(tmp_path):
    path = tmp_path / "scoring_rules.json"
    path.write_text(json.dumps({"days_cap": 10}), encoding="utf-8")
    env = {"NAVIGATOR_SCORING_RULES": json.dumps({"days_cap": 55}), "NAVIGATOR_SCORING_RULES_FILE": str(path)}
    assert load_rules(env).days_cap == 55


def test_defaults_when_nothing_configured():
    rules = load_rules({})
    assert rules == DEFAULT_RULES
    assert rules.to_dict() == {
        "segment_weights": {"A": 40, "B": 25, "C": 10},
        "points_per_day": 1,
        "days_cap": 40,
        "open_follow_up_bonus": 20,
        "recent_visit_days": 7,
        "max_score": 100,
    }
    assert load_rules({"NAVIGATOR_SCORING_RULES": "", "NAVIGATOR_SCORING_RULES_FILE": ""}) == DEFAULT_RULES


def test_boundary_7_vs_8_days():
    seven = score_hcp("A", 7, 2)
    assert seven.score == 0
    assert seven.reason == "Visited 7 days ago (within 7 days)"
    eight = score_hcp("A", 8, 0)
    assert eight.score == 48
    assert eight.reason == "Segment A (+40), 8 days since last visit (+8)"


def test_exactly_40_days_is_not_marked_capped():
    result = score_hcp("A", 40, 0)
    assert result.score == 80
    assert result.reason == "Segment A (+40), 40 days since last visit (+40)"
    assert result.factors[1].detail == "40 days since last visit"


def test_raw_100_has_no_cap_suffix():
    result = score_hcp("A", 60, 1)
    assert result.score == 100
    assert result.reason == "Segment A (+40), 60 days since last visit (+40, capped), 1 open follow-up (+20)"


def test_raw_over_100_gets_cap_suffix():
    rules = ScoringRules(segment_weights={"A": 60, "B": 25, "C": 10})
    result = score_hcp("A", 50, 2, rules)
    assert sum(factor.points for factor in result.factors) == 120
    assert result.score == 100
    assert result.reason == (
        "Segment A (+60), 50 days since last visit (+40, capped), 2 open follow-ups (+20) → capped at 100"
    )


def test_custom_points_per_day_and_cap():
    rules = ScoringRules(points_per_day=2, days_cap=30)
    assert score_hcp("C", 10, 0, rules).reason == "Segment C (+10), 10 days since last visit (+20)"
    capped = score_hcp("C", 20, 0, rules)
    assert capped.score == 40
    assert capped.reason == "Segment C (+10), 20 days since last visit (+30, capped)"


def test_follow_up_bonus_is_flat():
    assert score_hcp("B", 10, 1).score == score_hcp("B", 10, 3).score == 55
    assert score_hcp("B", 10, 3).factors[-1].detail == "3 open follow-ups"


def test_to_dict_is_json_safe():
    payload = score_hcp("C", 12, 0).to_dict()
    assert payload == {
        "score": 22,
        "reason": "Segment C (+10), 12 days since last visit (+12)",
        "factors": [
            {"name": "segment", "points": 10, "detail": "Segment C"},
            {"name": "days_since_last_visit", "points": 12, "detail": "12 days since last visit"},
        ],
    }
    json.dumps(payload)


def test_unknown_segment_rejected():
    with pytest.raises(ValueError, match="unknown segment"):
        score_hcp("Z", 10, 0)


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"segment_weights": {"A": 40, "B": 25}}, "weights for C"),
        ({"segment_weights": {"A": -1, "B": 25, "C": 10}}, "non-negative"),
        ({"segment_weights": {"A": "40", "B": 25, "C": 10}}, "non-negative"),
        ({"segment_weights": {"A": True, "B": 25, "C": 10}}, "non-negative"),
        ({"segment_weights": [40, 25, 10]}, "must be an object"),
        ({"days_cap": -5}, "days_cap"),
        ({"points_per_day": 1.5}, "points_per_day"),
        ({"bonus": 3}, "unknown scoring rule"),
    ],
)
def test_invalid_rules_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        rules_from_dict(overrides)


def test_invalid_rules_rejected_from_env_and_file(tmp_path):
    with pytest.raises(ValueError, match="not valid JSON"):
        load_rules({"NAVIGATOR_SCORING_RULES": "{not json"})
    with pytest.raises(ValueError, match="JSON object"):
        load_rules({"NAVIGATOR_SCORING_RULES": "[1, 2]"})
    with pytest.raises(ValueError, match="cannot read"):
        load_rules({"NAVIGATOR_SCORING_RULES_FILE": str(tmp_path / "missing.json")})
