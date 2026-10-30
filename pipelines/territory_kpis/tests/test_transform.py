from datetime import date

import numpy as np
import pytest
from pyspark.sql import functions as F

from pipelines.territory_kpis.tests.conftest import (
    FOLLOW_UP_SCHEMA,
    MONDAY,
    NEXT_MONDAY,
    REP_SCHEMA,
    SALES_SCHEMA,
    SUNDAY,
    TERRITORY_SCHEMA,
    TUESDAY,
    VISIT_SCHEMA,
    visit,
)
from pipelines.territory_kpis.transform import (
    OUTPUT_COLUMNS,
    aggregate_open_follow_ups,
    aggregate_sales,
    aggregate_visits,
    assemble_kpis,
    build_territory_kpis,
    count_reps,
    round_half_even,
    week_start,
)


def rows(df):
    return [r.asDict() for r in df.collect()]


@pytest.mark.parametrize(
    "value, expected",
    [
        (MONDAY, MONDAY),
        (TUESDAY, MONDAY),
        (SUNDAY, MONDAY),
        (NEXT_MONDAY, NEXT_MONDAY),
        (date(2025, 1, 1), date(2024, 12, 30)),
    ],
)
def test_week_start_maps_to_monday(spark, value, expected):
    df = spark.createDataFrame([(value,)], "d date").select(week_start(F.col("d")).alias("week"))
    assert df.first()["week"] == expected
    assert df.schema["week"].dataType.simpleString() == "date"


@pytest.mark.parametrize(
    "value, scale, expected",
    [(0.03125, 4, 0.0312), (15.625, 2, 15.62), (15.635, 2, 15.64), (3.0, 2, 3.0), (1.23456, 2, 1.23), (2.5, 0, 2.0)],
)
def test_round_half_even_matches_numpy(spark, value, scale, expected):
    assert np.round(value, scale) == expected  # the pandas/numpy behaviour we are mirroring
    df = spark.createDataFrame([(value,)], "x double")
    assert df.select(round_half_even(F.col("x"), scale).alias("r")).first()["r"] == expected


def test_round_half_even_differs_from_spark_round_on_ties(spark):
    df = spark.createDataFrame([(0.03125,), (15.625,)], "x double")
    got = df.select(round_half_even(F.col("x"), 4).alias("ours"), F.round(F.col("x"), 4).alias("spark")).collect()
    assert [r["ours"] for r in got] == [0.0312, 15.625]
    assert [r["spark"] for r in got] == [0.0313, 15.625]


def test_aggregate_visits(make_df):
    visits = make_df(
        [
            visit("V1", hcp_id="H1", channel="face_to_face", visit_date=MONDAY, duration=10),
            visit("V2", hcp_id="H1", channel="virtual", visit_date=TUESDAY, duration=15),
            visit("V3", hcp_id="H2", channel="face_to_face", visit_date=SUNDAY, duration=20),
            visit("V4", hcp_id="H3", channel="phone", visit_date=NEXT_MONDAY, duration=45),
            visit("V5", territory_id="T002", hcp_id="H9", channel="face_to_face", visit_date=TUESDAY, duration=30),
        ],
        VISIT_SCHEMA,
    )
    out = {(r["territory_id"], r["week"]): r for r in rows(aggregate_visits(visits))}
    assert set(out) == {("T001", MONDAY), ("T001", NEXT_MONDAY), ("T002", MONDAY)}
    wk1 = out[("T001", MONDAY)]
    assert (wk1["visits"], wk1["unique_hcps"], wk1["f2f_visits"]) == (3, 2, 2)
    assert wk1["avg_duration_min"] == 15.0
    assert wk1["f2f_share"] == 0.6667
    wk2 = out[("T001", NEXT_MONDAY)]
    assert (wk2["visits"], wk2["f2f_visits"], wk2["f2f_share"], wk2["avg_duration_min"]) == (1, 0, 0.0, 45.0)
    assert out[("T002", MONDAY)]["f2f_share"] == 1.0


def test_aggregate_open_follow_ups_resolves_territory_via_reps(make_df):
    reps = make_df([{"rep_id": "R1", "territory_id": "T001"}, {"rep_id": "R2", "territory_id": "T002"}], REP_SCHEMA)
    follow_ups = make_df(
        [
            {"follow_up_id": "F1", "rep_id": "R1", "due_date": TUESDAY, "status": "open"},
            {"follow_up_id": "F2", "rep_id": "R1", "due_date": SUNDAY, "status": "open"},
            {"follow_up_id": "F3", "rep_id": "R1", "due_date": MONDAY, "status": "done"},
            {"follow_up_id": "F4", "rep_id": "R2", "due_date": NEXT_MONDAY, "status": "open"},
        ],
        FOLLOW_UP_SCHEMA,
    )
    agg = aggregate_open_follow_ups(follow_ups, reps)
    out = {(r["territory_id"], r["week"]): r["open_follow_ups"] for r in rows(agg)}
    assert out == {("T001", MONDAY): 2, ("T002", NEXT_MONDAY): 1}


def test_aggregate_sales(make_df):
    sales = make_df(
        [
            {"territory_id": "T001", "week": MONDAY, "product": "A", "units": 10, "revenue_gbp": 100.004},
            {"territory_id": "T001", "week": MONDAY, "product": "B", "units": 5, "revenue_gbp": 50.002},
            {"territory_id": "T001", "week": NEXT_MONDAY, "product": "A", "units": 1, "revenue_gbp": 9.99},
        ],
        SALES_SCHEMA,
    )
    out = {(r["territory_id"], r["week"]): r for r in rows(aggregate_sales(sales))}
    assert out[("T001", MONDAY)]["units"] == 15
    assert out[("T001", MONDAY)]["revenue_gbp"] == 150.01
    assert out[("T001", NEXT_MONDAY)]["units"] == 1


def test_count_reps(make_df):
    reps = make_df(
        [
            {"rep_id": "R1", "territory_id": "T001"},
            {"rep_id": "R2", "territory_id": "T001"},
            {"rep_id": "R3", "territory_id": "T002"},
        ],
        REP_SCHEMA,
    )
    assert {r["territory_id"]: r["rep_count"] for r in rows(count_reps(reps))} == {"T001": 2, "T002": 1}


def test_assemble_kpis_fills_zeros_when_no_visits(make_df, spark):
    sales = make_df(
        [
            {"territory_id": "T001", "week": MONDAY, "product": "A", "units": 10, "revenue_gbp": 100.0},
            {"territory_id": "T001", "week": NEXT_MONDAY, "product": "A", "units": 7, "revenue_gbp": 70.0},
        ],
        SALES_SCHEMA,
    )
    visit_metrics = spark.createDataFrame(
        [("T001", MONDAY, 4, 3, 1, 25.0, 0.25)],
        "territory_id string, week date, visits long, unique_hcps long, f2f_visits long, "
        "avg_duration_min double, f2f_share double",
    )
    open_fu = spark.createDataFrame([("T001", MONDAY, 2)], "territory_id string, week date, open_follow_ups long")
    reps = spark.createDataFrame([("T001", 2)], "territory_id string, rep_count long")
    territories = make_df([{"territory_id": "T001", "region": "North"}], TERRITORY_SCHEMA)

    out = assemble_kpis(aggregate_sales(sales), visit_metrics, open_fu, reps, territories)
    assert out.columns == OUTPUT_COLUMNS
    got = rows(out)
    assert [(r["territory_id"], r["week"]) for r in got] == [("T001", MONDAY), ("T001", NEXT_MONDAY)]

    with_visits = got[0]
    assert with_visits["region"] == "North"
    assert with_visits["visits_per_rep"] == 2.0
    assert with_visits["revenue_per_visit"] == 25.0
    assert with_visits["open_follow_ups"] == 2

    no_visits = got[1]
    assert [no_visits[c] for c in ["visits", "unique_hcps", "f2f_visits", "open_follow_ups"]] == [0, 0, 0, 0]
    assert (no_visits["f2f_share"], no_visits["avg_duration_min"]) == (0.0, 0.0)
    assert no_visits["visits_per_rep"] == 0.0
    assert no_visits["revenue_per_visit"] == 0.0
    assert no_visits["units"] == 7
    assert no_visits["revenue_gbp"] == 70.0


def test_build_territory_kpis_end_to_end_tiny(make_df):
    territories = make_df([{"territory_id": "T001", "region": "North"}], TERRITORY_SCHEMA)
    reps = make_df([{"rep_id": "R1", "territory_id": "T001"}], REP_SCHEMA)
    visits = make_df(
        [visit("V1", visit_date=SUNDAY, duration=30), visit("V2", hcp_id="H2", visit_date=TUESDAY)], VISIT_SCHEMA
    )
    follow_ups = make_df(
        [{"follow_up_id": "F1", "rep_id": "R1", "due_date": TUESDAY, "status": "open"}], FOLLOW_UP_SCHEMA
    )
    sales = make_df(
        [{"territory_id": "T001", "week": MONDAY, "product": "A", "units": 3, "revenue_gbp": 99.0}], SALES_SCHEMA
    )

    out = rows(build_territory_kpis(territories, reps, visits, follow_ups, sales))
    assert len(out) == 1
    r = out[0]
    assert r["week"] == MONDAY
    assert (r["visits"], r["unique_hcps"], r["f2f_visits"], r["f2f_share"]) == (2, 2, 2, 1.0)
    assert r["avg_duration_min"] == 25.0
    assert (r["open_follow_ups"], r["rep_count"], r["visits_per_rep"]) == (1, 1, 2.0)
    assert (r["units"], r["revenue_gbp"], r["revenue_per_visit"]) == (3, 99.0, 49.5)
