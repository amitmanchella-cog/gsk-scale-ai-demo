"""Plan CSV export (S4): AC6 columns/ordering/headers, S4.1 comma quoting, S4.2 empty plan, 404."""

import csv
import io

from navigator_app.deps import get_store
from navigator_app.plans import PlanStore, build_plan, plan_to_csv
from navigator_app.views import territory_hcps

HEADER = ["day", "hcp_id", "hcp_name", "specialty", "segment", "score", "reason"]
ISLA_XU = "H00733"  # T001, Segment A, 51 days since last visit, 1 open follow-up, score 100
ISLA_XU_REASON = "Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)"


def t001_hcp_ids(count: int) -> list[str]:
    return list(territory_hcps(get_store(), "T001")["hcp_id"].head(count))


def add(client, rep_id, hcp_id, day):
    r = client.post(f"/reps/{rep_id}/plan/visits", json={"hcp_id": hcp_id, "day": day})
    assert r.status_code == 201, r.text
    return r.json()


def export(client, rep_id="R001"):
    r = client.get(f"/reps/{rep_id}/plan/export.csv")
    assert r.status_code == 200, r.text
    return r, list(csv.reader(io.StringIO(r.text)))


def test_ac6_csv_columns_and_rows(client):
    hcp_ids = t001_hcp_ids(5)
    # Insert out of day/score order so the export has to sort: Wed, Mon (low score), Fri, Mon (high score), Mon.
    add(client, "R001", hcp_ids[2], "Wed")
    add(client, "R001", hcp_ids[4], "Mon")
    add(client, "R001", hcp_ids[1], "Fri")
    plan = add(client, "R001", hcp_ids[0], "Mon")
    plan = add(client, "R001", hcp_ids[3], "Mon")
    assert plan["total_visits"] == 5
    by_id = {v["hcp_id"]: v for d in plan["days"] for v in d["visits"]}

    r, rows = export(client)
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    assert r.headers["content-disposition"] == 'attachment; filename="plan_R001_2025-09-29.csv"'
    assert r.text.startswith(",".join(HEADER) + "\r\n")
    assert r.text.count("\r\n") == 6  # header + 5 rows, RFC 4180 line endings

    assert rows[0] == HEADER
    assert len(rows) == 6
    assert [row[0] for row in rows[1:]] == ["Mon", "Mon", "Mon", "Wed", "Fri"]
    monday = rows[1:4]
    scores = [int(row[5]) for row in monday]
    assert scores == sorted(scores, reverse=True)
    assert sorted(row[1] for row in monday) == sorted([hcp_ids[0], hcp_ids[3], hcp_ids[4]])
    for row in rows[1:]:
        visit = by_id[row[1]]
        assert row[1:] == [
            visit["hcp_id"],
            visit["hcp_name"],
            visit["specialty"],
            visit["segment"],
            str(visit["score"]),
            visit["reason"],
        ]


def test_reason_commas_quoted(client):
    add(client, "R001", ISLA_XU, "Tue")
    r, rows = export(client)
    assert rows[1] == ["Tue", ISLA_XU, "Dr Isla Xu", "GP", "A", "100", ISLA_XU_REASON]
    assert f'"{ISLA_XU_REASON}"' in r.text  # the comma-bearing reason is one quoted field
    assert len(rows[1]) == len(HEADER)


def test_empty_plan_header_only(client):
    r, rows = export(client)
    assert r.text == ",".join(HEADER) + "\r\n"
    assert rows == [HEADER]
    assert r.headers["content-disposition"] == 'attachment; filename="plan_R001_2025-09-29.csv"'


def test_export_unknown_rep_404(client):
    r = client.get("/reps/R999/plan/export.csv")
    assert r.status_code == 404
    assert r.json() == {"detail": "rep R999 not found"}


def test_plan_to_csv_orders_by_score_then_name():
    plan_store = PlanStore()
    hcp_ids = t001_hcp_ids(4)
    for hcp_id in hcp_ids:
        plan_store.add_visit("R001", hcp_id, "Thu", 6)
    plan = build_plan(get_store(), "R001", plan_store=plan_store)
    rows = list(csv.reader(io.StringIO(plan_to_csv(plan))))[1:]
    assert [(int(row[5]), row[2]) for row in rows] == sorted(
        ((v.score, v.hcp_name) for v in plan.days[3].visits), key=lambda t: (-t[0], t[1])
    )
