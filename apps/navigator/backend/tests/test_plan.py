"""Weekly plan builder (S3): AC4, AC5, S3.1–S3.4 plus 404s, clear, counts/capacity and week dates."""

from datetime import date

import pytest
from navigator_app.deps import get_store
from navigator_app.plans import DAYS, PlanStore, build_plan, week_start
from navigator_app.views import territory_hcps

ISLA_XU = "H00733"  # T001, Segment A, last visit 2025-08-09 = 51 days before 2025-09-29, score 100
ISLA_XU_REASON = "Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)"
T001_OVERDUE_SEGMENT_A = 12


def t001_hcp_ids(count: int) -> list[str]:
    """Top-scored T001 HCPs (deterministic on the repo data)."""
    return list(territory_hcps(get_store(), "T001")["hcp_id"].head(count))


def add(client, rep_id, hcp_id, day, expected=201):
    r = client.post(f"/reps/{rep_id}/plan/visits", json={"hcp_id": hcp_id, "day": day})
    assert r.status_code == expected, r.text
    return r.json()


def day(plan: dict, code: str) -> dict:
    return next(d for d in plan["days"] if d["day"] == code)


def test_empty_plan_shape_and_week_dates(client):
    r = client.get("/reps/R001/plan")
    assert r.status_code == 200
    plan = r.json()
    assert set(plan) == {
        "rep_id",
        "territory_id",
        "week_start",
        "as_of",
        "max_visits_per_day",
        "total_visits",
        "days",
        "warnings",
    }
    assert plan["rep_id"] == "R001"
    assert plan["territory_id"] == "T001"
    assert plan["as_of"] == "2025-09-29"
    assert plan["week_start"] == "2025-09-29"  # the as-of date is a Monday
    assert plan["max_visits_per_day"] == 6
    assert plan["total_visits"] == 0
    assert [d["day"] for d in plan["days"]] == list(DAYS)
    assert [d["date"] for d in plan["days"]] == ["2025-09-29", "2025-09-30", "2025-10-01", "2025-10-02", "2025-10-03"]
    assert all(d["count"] == 0 and d["capacity"] == 6 and d["visits"] == [] for d in plan["days"])


def test_week_start_is_monday_of_as_of_week(client):
    assert week_start(date(2025, 9, 29)) == date(2025, 9, 29)
    assert week_start(date(2025, 10, 2)) == date(2025, 9, 29)
    assert week_start(date(2025, 10, 5)) == date(2025, 9, 29)  # Sunday still belongs to the Monday-29 week
    plan = client.get("/reps/R001/plan", params={"as_of": "2025-10-02"}).json()
    assert plan["as_of"] == "2025-10-02"
    assert plan["week_start"] == "2025-09-29"
    assert day(plan, "Fri")["date"] == "2025-10-03"


def test_ac4_seventh_visit_blocked(client):
    hcp_ids = t001_hcp_ids(7)
    for hcp_id in hcp_ids[:6]:
        plan = add(client, "R001", hcp_id, "Tue")
    assert day(plan, "Tue")["count"] == 6
    assert plan["total_visits"] == 6

    r = client.post("/reps/R001/plan/visits", json={"hcp_id": hcp_ids[6], "day": "Tue"})
    assert r.status_code == 409
    assert r.json() == {"detail": "Tuesday already has 6 visits (max 6)"}

    after = client.get("/reps/R001/plan").json()
    assert after == plan  # unchanged
    assert [v["hcp_id"] for v in day(after, "Tue")["visits"]] == hcp_ids[:6]
    # the same HCP still fits on another day
    assert day(add(client, "R001", hcp_ids[6], "Wed"), "Wed")["count"] == 1


def test_capacity_from_env(client, monkeypatch):
    monkeypatch.setenv("NAVIGATOR_MAX_VISITS_PER_DAY", "2")
    hcp_ids = t001_hcp_ids(3)
    plan = client.get("/reps/R001/plan").json()
    assert plan["max_visits_per_day"] == 2
    assert all(d["capacity"] == 2 for d in plan["days"])
    add(client, "R001", hcp_ids[0], "Mon")
    add(client, "R001", hcp_ids[1], "Mon")
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": hcp_ids[2], "day": "Mon"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Monday already has 2 visits (max 2)"


def test_ac5_overdue_segment_a_warning(client):
    plan = client.get("/reps/R001/plan").json()
    overdue = [w for w in plan["warnings"] if w["type"] == "overdue_segment_a"]
    assert len(overdue) == T001_OVERDUE_SEGMENT_A
    assert plan["warnings"] == overdue  # nothing else on an empty plan
    isla = next(w for w in overdue if w["hcp_id"] == ISLA_XU)
    assert isla == {
        "type": "overdue_segment_a",
        "hcp_id": ISLA_XU,
        "hcp_name": "Dr Isla Xu",
        "days": [],
        "message": "Dr Isla Xu (Segment A) is 51 days overdue and not planned",
    }
    # ordered by days overdue, most overdue first
    days_overdue = [int(w["message"].split(" is ")[1].split(" days")[0]) for w in overdue]
    assert days_overdue == sorted(days_overdue, reverse=True)
    assert overdue[0]["message"].startswith("Dr Priya Walsh (Segment A) is 109 days overdue")

    plan = add(client, "R001", ISLA_XU, "Mon")
    overdue = [w for w in plan["warnings"] if w["type"] == "overdue_segment_a"]
    assert len(overdue) == T001_OVERDUE_SEGMENT_A - 1
    assert ISLA_XU not in {w["hcp_id"] for w in overdue}
    visit = day(plan, "Mon")["visits"][0]
    assert visit == {
        "visit_id": 1,
        "hcp_id": ISLA_XU,
        "hcp_name": "Dr Isla Xu",
        "specialty": "GP",
        "segment": "A",
        "score": 100,
        "reason": ISLA_XU_REASON,
    }


def test_overdue_threshold_from_env(client, monkeypatch):
    monkeypatch.setenv("NAVIGATOR_OVERDUE_DAYS", "60")
    overdue = [w for w in client.get("/reps/R001/plan").json()["warnings"] if w["type"] == "overdue_segment_a"]
    assert {w["hcp_id"] for w in overdue} == {"H00694", "H00250", "H01014", "H00082", "H01039"}  # > 60 days
    assert ISLA_XU not in {w["hcp_id"] for w in overdue}  # 51 days is no longer overdue


def test_never_visited_segment_a_warning(client):
    store = get_store()
    hcps = store["hcps"]
    territory = str(hcps.loc[hcps["hcp_id"] == "H00052", "territory_id"].iloc[0])
    view = territory_hcps(store, territory)
    never = view[(view["segment"] == "A") & view["days_since_last_visit"].isna()]
    rep_id = str(store["reps"].loc[store["reps"]["territory_id"] == territory, "rep_id"].iloc[0])
    plan = client.get(f"/reps/{rep_id}/plan").json()
    overdue = [w for w in plan["warnings"] if w["type"] == "overdue_segment_a"]
    never_warnings = [w for w in overdue if "never been visited" in w["message"]]
    assert len(never_warnings) == len(never)
    assert overdue[: len(never)] == never_warnings  # never-visited come first
    for w in never_warnings:
        assert w["message"] == f"{w['hcp_name']} (Segment A) has never been visited and is not planned"


def test_duplicate_warning(client):
    plan = add(client, "R001", ISLA_XU, "Mon")
    assert not [w for w in plan["warnings"] if w["type"] == "duplicate"]

    plan = add(client, "R001", ISLA_XU, "Tue")  # allowed, warned (S3.1)
    assert plan["total_visits"] == 2
    duplicates = [w for w in plan["warnings"] if w["type"] == "duplicate"]
    assert duplicates == [
        {
            "type": "duplicate",
            "hcp_id": ISLA_XU,
            "hcp_name": "Dr Isla Xu",
            "days": ["Mon", "Tue"],
            "message": "Dr Isla Xu is planned twice (Mon, Tue)",
        }
    ]
    assert plan["warnings"][0]["type"] == "duplicate"  # duplicates are listed before overdue warnings

    plan = add(client, "R001", ISLA_XU, "Tue")  # same day twice is also a duplicate
    duplicates = [w for w in plan["warnings"] if w["type"] == "duplicate"]
    assert duplicates[0]["days"] == ["Mon", "Tue", "Tue"]
    assert duplicates[0]["message"] == "Dr Isla Xu is planned 3 times (Mon, Tue, Tue)"


def test_remove_visit(client):
    plan = add(client, "R001", ISLA_XU, "Mon")
    plan = add(client, "R001", ISLA_XU, "Tue")
    mon_id = day(plan, "Mon")["visits"][0]["visit_id"]
    tue_id = day(plan, "Tue")["visits"][0]["visit_id"]
    assert (mon_id, tue_id) == (1, 2)

    r = client.delete(f"/reps/R001/plan/visits/{mon_id}")
    assert r.status_code == 200
    plan = r.json()
    assert day(plan, "Mon")["visits"] == []
    assert [v["visit_id"] for v in day(plan, "Tue")["visits"]] == [tue_id]
    assert plan["total_visits"] == 1
    assert not [w for w in plan["warnings"] if w["type"] == "duplicate"]  # recomputed (S3.2)
    assert ISLA_XU not in {w["hcp_id"] for w in plan["warnings"]}

    plan = client.delete(f"/reps/R001/plan/visits/{tue_id}").json()
    assert plan["total_visits"] == 0
    assert ISLA_XU in {w["hcp_id"] for w in plan["warnings"]}  # overdue warning is back

    assert client.delete(f"/reps/R001/plan/visits/{mon_id}").status_code == 404  # already removed
    assert client.delete("/reps/R001/plan/visits/999").status_code == 404
    assert client.delete("/reps/R999/plan/visits/1").status_code == 404

    # visit ids keep increasing within a plan; they are never reused
    assert day(add(client, "R001", ISLA_XU, "Fri"), "Fri")["visits"][0]["visit_id"] == 3


def test_plan_is_per_rep(client):
    add(client, "R001", ISLA_XU, "Mon")
    r002_hcp = str(territory_hcps(get_store(), "T002")["hcp_id"].iloc[0])
    other = add(client, "R002", r002_hcp, "Mon")
    assert other["rep_id"] == "R002"
    assert other["territory_id"] == "T002"
    assert other["total_visits"] == 1
    assert day(other, "Mon")["visits"][0]["hcp_id"] == r002_hcp
    assert day(other, "Mon")["visits"][0]["visit_id"] == 1  # ids are per plan

    mine = client.get("/reps/R001/plan").json()
    assert [v["hcp_id"] for v in day(mine, "Mon")["visits"]] == [ISLA_XU]

    client.delete("/reps/R002/plan")
    assert client.get("/reps/R001/plan").json()["total_visits"] == 1


def test_foreign_hcp_422(client):
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": "H00002", "day": "Tue"})  # H00002 is in T005
    assert r.status_code == 422
    assert r.json() == {"detail": "HCP H00002 is not in territory T001"}
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": "H00052", "day": "Mon"})  # Dr Chloe Xu is in T011
    assert r.status_code == 422
    assert client.get("/reps/R001/plan").json()["total_visits"] == 0


def test_bad_day_422(client):
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": ISLA_XU, "day": "Sat"})
    assert r.status_code == 422
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": ISLA_XU})
    assert r.status_code == 422
    assert client.get("/reps/R001/plan").json()["total_visits"] == 0


def test_unknown_rep_and_hcp_404(client):
    assert client.get("/reps/R999/plan").status_code == 404
    assert client.delete("/reps/R999/plan").status_code == 404
    r = client.post("/reps/R999/plan/visits", json={"hcp_id": ISLA_XU, "day": "Mon"})
    assert r.status_code == 404
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": "H99999", "day": "Mon"})
    assert r.status_code == 404
    assert r.json()["detail"] == "HCP H99999 not found"


def test_day_full_checked_before_hcp_validation(client):
    for hcp_id in t001_hcp_ids(6):
        add(client, "R001", hcp_id, "Fri")
    r = client.post("/reps/R001/plan/visits", json={"hcp_id": "H00002", "day": "Fri"})
    assert r.status_code == 409


def test_clear_plan(client):
    for hcp_id, code in zip(t001_hcp_ids(3), ("Mon", "Wed", "Fri")):
        add(client, "R001", hcp_id, code)
    assert client.get("/reps/R001/plan").json()["total_visits"] == 3

    r = client.delete("/reps/R001/plan")
    assert r.status_code == 200
    plan = r.json()
    assert plan["total_visits"] == 0
    assert all(d["visits"] == [] for d in plan["days"])
    assert len(plan["warnings"]) == T001_OVERDUE_SEGMENT_A
    assert client.delete("/reps/R001/plan").status_code == 200  # idempotent
    assert day(add(client, "R001", ISLA_XU, "Mon"), "Mon")["visits"][0]["visit_id"] == 1  # counter restarts


def test_counts_and_capacity_across_days(client):
    hcp_ids = t001_hcp_ids(6)
    for i, hcp_id in enumerate(hcp_ids):
        plan = add(client, "R001", hcp_id, DAYS[i % 5])
    assert [d["count"] for d in plan["days"]] == [2, 1, 1, 1, 1]
    assert plan["total_visits"] == 6
    assert all(d["count"] == len(d["visits"]) and d["capacity"] == plan["max_visits_per_day"] for d in plan["days"])
    assert [v["hcp_id"] for v in day(plan, "Mon")["visits"]] == [hcp_ids[0], hcp_ids[5]]  # insertion order


def test_build_plan_follows_as_of(client):
    store = get_store()
    plan_store = PlanStore()
    plan_store.add_visit("R001", ISLA_XU, "Mon", 6)
    earlier = build_plan(store, "R001", as_of=date(2025, 8, 20), plan_store=plan_store)
    assert earlier.week_start == date(2025, 8, 18)
    visit = earlier.days[0].visits[0]
    assert visit.reason == "Segment A (+40), 11 days since last visit (+11), 1 open follow-up (+20)"
    assert visit.score == 71
    with pytest.raises(Exception, match="rep R999 not found"):
        build_plan(store, "R999", plan_store=plan_store)
