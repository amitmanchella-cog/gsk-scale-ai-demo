"""Field-level precision, recall and F1 for the extraction provider."""

from __future__ import annotations

from typing import Any

from pda_api.providers import LLMProvider


def predicted_fields(provider: LLMProvider, text: str) -> set[tuple[str, Any]]:
    """Flatten an extraction into comparable (field, value) pairs."""
    design = provider.extract_design(text)
    fields: set[tuple[str, Any]] = set()
    if design.population.min_age is not None:
        fields.add(("min_age", float(design.population.min_age)))
    if design.population.max_age is not None:
        fields.add(("max_age", float(design.population.max_age)))
    fields.add(("n_inclusion", sum(1 for c in design.criteria if c.kind == "inclusion")))
    fields.add(("n_exclusion", sum(1 for c in design.criteria if c.kind == "exclusion")))
    for index, criterion in enumerate(design.criteria):
        fields.add((f"category[{index}]", criterion.category))
        if criterion.parameter and criterion.parameter != "age":
            if criterion.lower is not None:
                fields.add((f"{criterion.parameter}_lower", float(criterion.lower)))
            if criterion.upper is not None:
                fields.add((f"{criterion.parameter}_upper", float(criterion.upper)))
    return fields


def expected_fields(expected: dict[str, Any]) -> set[tuple[str, Any]]:
    fields: set[tuple[str, Any]] = set()
    for key, value in expected.items():
        if key == "categories":
            fields.update((f"category[{index}]", category) for index, category in enumerate(value))
        elif key.startswith("n_"):
            fields.add((key, int(value)))
        else:
            fields.add((key, float(value)))
    return fields


def field_f1(provider: LLMProvider, labelled: list[dict[str, Any]]) -> dict[str, float]:
    """Micro-averaged precision, recall and F1 over all labelled texts."""
    true_positive = false_positive = false_negative = 0
    for example in labelled:
        predicted = predicted_fields(provider, example["text"])
        expected = expected_fields(example["expected"])
        true_positive += len(predicted & expected)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
