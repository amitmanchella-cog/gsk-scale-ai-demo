"""Scores that make versions comparable: participant burden and a cost proxy."""

from __future__ import annotations

from csd_core.domain.models import Model, StudyGraph


class Score(Model):
    """Lower is better on every measure."""

    visit_count: int
    patient_time_minutes: int
    """Total patient time: the sum of visit durations, a visit lasting as long as its activities."""
    cost_proxy: float
    """The sum of the unit costs of every scheduled activity, per participant."""


def visit_durations(graph: StudyGraph) -> dict[str, int]:
    """Minutes per visit: the summed duration of the activities scheduled at it."""
    minutes = {activity.id: activity.duration_minutes for activity in graph.plan.activities}
    durations = {visit.id: 0 for visit in graph.plan.visits}
    for cell in graph.plan.schedule:
        durations[cell.visit_id] += minutes[cell.activity_id]
    return durations


def score(graph: StudyGraph) -> Score:
    costs = {activity.id: activity.unit_cost for activity in graph.plan.activities}
    return Score(
        visit_count=len(graph.plan.visits),
        patient_time_minutes=sum(visit_durations(graph).values()),
        cost_proxy=sum(costs[cell.activity_id] for cell in graph.plan.schedule),
    )
