"""Generate synthetic pharma field-force data (no real people, products or places).

Outputs Parquet files to data/ :
  territories.parquet, reps.parquet, hcps.parquet, visits.parquet,
  follow_ups.parquet, weekly_sales.parquet  (~10k rows total)

Deterministic: seeded with 42 so expected outputs are reproducible.
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
REGIONS = ["North", "South", "East", "West", "Central"]
SPECIALTIES = ["Cardiology", "Endocrinology", "Pulmonology", "Oncology", "GP", "Neurology"]
SEGMENTS = ["A", "B", "C"]
PRODUCTS = ["Zentrava", "Corvalis", "Pulmexa", "Nevrosyn"]
FIRST = ["Ada", "Ben", "Chloe", "Dev", "Esme", "Finn", "Grace", "Hugo", "Isla", "Jon",
         "Kira", "Leo", "Mia", "Noor", "Owen", "Priya", "Quinn", "Rhea", "Sam", "Tara"]
LAST = ["Okafor", "Lindqvist", "Marsh", "Nakamura", "Ortega", "Patel", "Quist", "Rossi",
        "Singh", "Thornton", "Udo", "Varga", "Walsh", "Xu", "Young", "Zamora"]
NOTES = ["Send dosing leaflet", "Book lunch & learn", "Share trial data", "Follow up on formulary"]
ANCHOR = date(2025, 9, 29)  # Monday; data covers the 26 weeks before this


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def generate(out_dir: Path, n_hcps: int = 1600, n_weeks: int = 26) -> dict[str, pd.DataFrame]:
    rng = random.Random(SEED)
    territories = pd.DataFrame(
        [
            {"territory_id": f"T{i:03d}", "territory_name": f"{REGIONS[i % 5]}-{i:02d}", "region": REGIONS[i % 5]}
            for i in range(1, 21)
        ]
    )
    reps = pd.DataFrame(
        [
            {
                "rep_id": f"R{i:03d}",
                "rep_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                "territory_id": territories.territory_id.iloc[(i - 1) % len(territories)],
                "hire_date": ANCHOR - timedelta(days=rng.randint(180, 2500)),
            }
            for i in range(1, 31)
        ]
    )
    hcps = pd.DataFrame(
        [
            {
                "hcp_id": f"H{i:05d}",
                "hcp_name": f"Dr {rng.choice(FIRST)} {rng.choice(LAST)}",
                "specialty": rng.choice(SPECIALTIES),
                "segment": rng.choices(SEGMENTS, weights=[2, 4, 4])[0],
                "territory_id": territories.territory_id.iloc[rng.randrange(len(territories))],
            }
            for i in range(1, n_hcps + 1)
        ]
    )
    rep_by_terr = reps.groupby("territory_id").rep_id.apply(list).to_dict()

    visits, follow_ups = [], []
    vid = fid = 0
    for h in hcps.itertuples(index=False):
        n_visits = {"A": rng.randint(3, 8), "B": rng.randint(1, 5), "C": rng.randint(0, 3)}[h.segment]
        for _ in range(n_visits):
            vid += 1
            d = ANCHOR - timedelta(days=rng.randint(0, n_weeks * 7 - 1))
            rep_id = rng.choice(rep_by_terr[h.territory_id])
            visits.append(
                {
                    "visit_id": f"V{vid:06d}",
                    "hcp_id": h.hcp_id,
                    "rep_id": rep_id,
                    "territory_id": h.territory_id,
                    "visit_date": d,
                    "channel": rng.choices(["face_to_face", "virtual", "phone"], weights=[6, 3, 1])[0],
                    "duration_min": rng.choice([10, 15, 20, 30, 45]),
                    "product": rng.choice(PRODUCTS),
                }
            )
            if rng.random() < 0.3:
                fid += 1
                follow_ups.append(
                    {
                        "follow_up_id": f"F{fid:05d}",
                        "visit_id": f"V{vid:06d}",
                        "hcp_id": h.hcp_id,
                        "rep_id": rep_id,
                        "due_date": d + timedelta(days=rng.randint(3, 21)),
                        "status": rng.choices(["open", "done"], weights=[4, 6])[0],
                        "note": rng.choice(NOTES),
                    }
                )
    visits_df = pd.DataFrame(visits)
    follow_df = pd.DataFrame(follow_ups)

    sales = []
    for t in territories.territory_id:
        base = rng.randint(40, 120)
        for w in range(n_weeks):
            wk = _week_start(ANCHOR - timedelta(weeks=n_weeks - w))
            for p in PRODUCTS:
                units = max(0, int(rng.gauss(base, base * 0.25)))
                sales.append(
                    {
                        "territory_id": t,
                        "week": wk,
                        "product": p,
                        "units": units,
                        "revenue_gbp": round(units * rng.uniform(38.0, 62.0), 2),
                    }
                )
    sales_df = pd.DataFrame(sales)

    frames = {
        "territories": territories,
        "reps": reps,
        "hcps": hcps,
        "visits": visits_df,
        "follow_ups": follow_df,
        "weekly_sales": sales_df,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    return frames


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent))
    args = ap.parse_args()
    frames = generate(Path(args.out))
    for k, v in frames.items():
        print(f"{k:14s} {len(v):6d} rows")
    print(f"total          {sum(len(v) for v in frames.values()):6d} rows")
