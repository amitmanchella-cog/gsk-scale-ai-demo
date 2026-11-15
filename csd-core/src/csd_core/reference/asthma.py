"""Synthetic reference study: Phase 3 asthma, Drug 100 mg vs placebo, 52 weeks.

All content is invented for the demo. No person-level data.
"""

from __future__ import annotations

from csd_core.domain.models import (
    Activity,
    Arm,
    Assignment,
    DesignActivity,
    Endpoint,
    Estimand,
    IntentGraph,
    Objective,
    OperationalStandard,
    PlanGraph,
    ScheduledActivity,
    StudyGraph,
    Timepoint,
    Visit,
)

REFERENCE_STUDY_ID = "asthma-ref"

# Visit order (by study day) and activity order of the schedule-of-activities grid.
VISIT_IDS = ("V-SCR", "V-RAND", "V-W4", "V-W12", "V-W24", "V-W52", "V-FU")
ACTIVITY_IDS = ("A-ICF", "A-ELIG", "A-SPIRO", "A-ACQ5", "A-VITALS", "A-LABS", "A-AE", "A-DISP")

# The expected visit-by-activity matrix of the reference study.
SCHEDULE: dict[str, tuple[str, ...]] = {
    "A-ICF": ("V-SCR",),
    "A-ELIG": ("V-SCR", "V-RAND"),
    "A-SPIRO": ("V-SCR", "V-RAND", "V-W4", "V-W12", "V-W24", "V-W52"),
    "A-ACQ5": ("V-RAND", "V-W4", "V-W12", "V-W24", "V-W52"),
    "A-VITALS": ("V-SCR", "V-RAND", "V-W4", "V-W12", "V-W24", "V-W52"),
    "A-LABS": ("V-SCR", "V-RAND", "V-W12", "V-W24", "V-W52"),
    "A-AE": ("V-W4", "V-W12", "V-W24", "V-W52", "V-FU"),
    "A-DISP": ("V-RAND", "V-W4", "V-W12", "V-W24"),
}


def reference_study() -> StudyGraph:
    intent = IntentGraph(
        objectives=(
            Objective(
                id="OBJ-PRIM",
                level="primary",
                text="To evaluate the effect of Drug 100 mg compared with placebo on lung function",
            ),
            Objective(
                id="OBJ-SEC-EXAC",
                level="secondary",
                text="To evaluate the effect of Drug 100 mg compared with placebo on asthma "
                "exacerbations",
            ),
            Objective(
                id="OBJ-SEC-CTRL",
                level="secondary",
                text="To evaluate the effect of Drug 100 mg compared with placebo on asthma "
                "control",
            ),
        ),
        endpoints=(
            Endpoint(
                id="EP-FEV1",
                name="Change from baseline in trough FEV1",
                level="primary",
                objective_id="OBJ-PRIM",
                timepoint=Timepoint(week=12),
                design_activity_id="DA-SPIRO",
            ),
            Endpoint(
                id="EP-EXAC",
                name="Annualised exacerbation rate",
                level="secondary",
                objective_id="OBJ-SEC-EXAC",
                timepoint=Timepoint(week=52),
                design_activity_id="DA-EXAC",
            ),
            Endpoint(
                id="EP-ACQ5",
                name="Change from baseline in ACQ-5 score",
                level="secondary",
                objective_id="OBJ-SEC-CTRL",
                timepoint=Timepoint(week=24),
                design_activity_id="DA-ACQ5",
            ),
        ),
        estimands=(
            Estimand(
                id="EST-FEV1",
                endpoint_id="EP-FEV1",
                population="Adults with moderate to severe asthma",
                intercurrent_event_strategy="Treatment policy",
                summary_measure="Difference in mean change from baseline",
            ),
            Estimand(
                id="EST-EXAC",
                endpoint_id="EP-EXAC",
                population="Adults with moderate to severe asthma",
                intercurrent_event_strategy="Treatment policy",
                summary_measure="Rate ratio",
            ),
            Estimand(
                id="EST-ACQ5",
                endpoint_id="EP-ACQ5",
                population="Adults with moderate to severe asthma",
                intercurrent_event_strategy="Treatment policy",
                summary_measure="Difference in mean change from baseline",
            ),
        ),
        design_activities=(
            DesignActivity(id="DA-SPIRO", name="Spirometry", purpose="Trough FEV1"),
            DesignActivity(id="DA-ACQ5", name="ACQ-5 questionnaire", purpose="Asthma control"),
            DesignActivity(
                id="DA-EXAC", name="Exacerbation assessment", purpose="Exacerbations and safety"
            ),
            DesignActivity(id="DA-LABS", name="Safety laboratory tests", purpose="Safety"),
            DesignActivity(id="DA-IP", name="Study intervention", purpose="Drug 100 mg or placebo"),
        ),
        arms=(
            Arm(id="ARM-DRUG", name="Drug 100 mg", intervention="Drug 100 mg", ratio=1),
            Arm(id="ARM-PBO", name="Placebo", intervention="Matching placebo", ratio=1),
        ),
        assignment=Assignment(method="randomised", blinding="double-blind", control="placebo"),
    )
    plan = PlanGraph(
        visits=(
            Visit(id="V-SCR", name="Screening", day=-14, window=7, kind="screening"),
            Visit(id="V-RAND", name="Randomisation", day=1, window=0, kind="randomisation"),
            Visit(id="V-W4", name="Week 4", day=29, window=3),
            Visit(id="V-W12", name="Week 12", day=85, window=3),
            Visit(id="V-W24", name="Week 24", day=169, window=7),
            Visit(id="V-W52", name="Week 52", day=365, window=7),
            Visit(id="V-FU", name="Follow-up", day=393, window=7, kind="follow_up", on_site=False),
        ),
        activities=(
            Activity(id="A-ICF", name="Informed consent", unit_cost=50, duration_minutes=30),
            Activity(id="A-ELIG", name="Eligibility check", unit_cost=80, duration_minutes=20),
            Activity(
                id="A-SPIRO",
                name="Spirometry",
                unit_cost=120,
                duration_minutes=45,
                design_activity_id="DA-SPIRO",
            ),
            Activity(
                id="A-ACQ5",
                name="ACQ-5",
                unit_cost=15,
                duration_minutes=10,
                design_activity_id="DA-ACQ5",
            ),
            Activity(id="A-VITALS", name="Vital signs", unit_cost=20, duration_minutes=10),
            Activity(
                id="A-LABS",
                name="Labs",
                unit_cost=150,
                duration_minutes=15,
                design_activity_id="DA-LABS",
            ),
            Activity(
                id="A-AE",
                name="Adverse event review",
                unit_cost=25,
                duration_minutes=15,
                design_activity_id="DA-EXAC",
            ),
            Activity(
                id="A-DISP",
                name="Study drug dispensing",
                unit_cost=40,
                duration_minutes=10,
                design_activity_id="DA-IP",
            ),
        ),
        standards=(
            OperationalStandard(
                id="STD-CONSENT",
                name="Informed consent at screening",
                activity_id="A-ICF",
                applies_to="screening",
            ),
            OperationalStandard(
                id="STD-ELIG",
                name="Eligibility check at screening",
                activity_id="A-ELIG",
                applies_to="screening",
            ),
            OperationalStandard(
                id="STD-VITALS",
                name="Vital signs at every on-site visit",
                activity_id="A-VITALS",
                applies_to="on_site",
            ),
            OperationalStandard(
                id="STD-AE",
                name="Adverse event review at every visit after randomisation",
                activity_id="A-AE",
                applies_to="post_baseline",
            ),
        ),
        schedule=tuple(
            ScheduledActivity(visit_id=visit_id, activity_id=activity_id)
            for activity_id in ACTIVITY_IDS
            for visit_id in SCHEDULE[activity_id]
        ),
    )
    return StudyGraph(
        title="A Phase 3, randomised, double-blind, placebo-controlled study of Drug 100 mg "
        "in adults with asthma",
        phase="Phase 3",
        indication="Asthma",
        duration_weeks=52,
        intent=intent,
        plan=plan,
    )
