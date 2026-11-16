"""Generate a synthetic snapshot in the exact ClinicalTrials.gov API v2 JSON shape.

Fallback for machines that cannot reach the API: ``fetch_snapshot.py`` calls this
when the request fails. IDs are prefixed ``SYN`` so synthetic rows can never be
mistaken for registry records. Output is deterministic for a given seed.

Usage: python scripts/generate_synthetic.py [--out data/raw] [--trials 600] [--seed 7]
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

CONDITIONS = {
    "asthma": "Asthma",
    "copd": "Chronic Obstructive Pulmonary Disease",
    "type_2_diabetes": "Type 2 Diabetes Mellitus",
}
COUNTRIES = [
    "United States",
    "Germany",
    "United Kingdom",
    "Spain",
    "Poland",
    "Japan",
    "Canada",
    "France",
    "Italy",
    "China",
]
WHY_STOPPED = [
    "Slow enrollment",
    "Low recruitment rate",
    "Sponsor business decision",
    "Lack of efficacy at interim analysis",
    "Safety concerns",
    "Funding withdrawn",
]
COMMON_EXCLUSIONS = [
    "Pregnant or breastfeeding women",
    "History of malignancy within 5 years",
    "Myocardial infarction or stroke within 6 months",
    "Active hepatitis B or C infection",
    "Participation in another clinical trial within 30 days",
    "Known hypersensitivity to the study drug",
    "Severe psychiatric disorder",
]


def eligibility(rng: random.Random, indication: str, min_age: int, max_age: int | None) -> str:
    age = f"Aged {min_age} to {max_age} years" if max_age else f"Aged {min_age} years or older"
    inclusion = [age, "Able to provide written informed consent"]
    exclusion = rng.sample(COMMON_EXCLUSIONS, rng.randint(2, 6))
    if indication == "type_2_diabetes":
        low = rng.choice([6.5, 7.0, 7.5])
        inclusion.append(f"HbA1c between {low}% and {rng.choice([9.5, 10.0, 10.5, 11.0])}%")
        inclusion.append(f"BMI between {rng.choice([20, 23, 25])} and {rng.choice([35, 40, 45])} kg/m2")
        exclusion.append(f"eGFR < {rng.choice([30, 45, 60])} mL/min/1.73m2")
    elif indication == "copd":
        inclusion.append(
            f"Post-bronchodilator FEV1 between {rng.choice([30, 40])}% and {rng.choice([70, 80])}% predicted"
        )
        inclusion.append(f"Smoking history of at least {rng.choice([10, 20])} pack-years")
    else:
        inclusion.append(
            f"Pre-bronchodilator FEV1 between {rng.choice([40, 50, 60])}% and {rng.choice([80, 90])}% predicted"
        )
        exclusion.append(f"Smoking history of more than {rng.choice([10, 20])} pack-years")
    return (
        "Inclusion Criteria:\n\n"
        + "\n".join(f"* {item}" for item in inclusion)
        + "\n\nExclusion Criteria:\n\n"
        + "\n".join(f"* {item}" for item in exclusion)
        + "\n"
    )


def study(rng: random.Random, index: int, indication: str, status: str) -> dict[str, Any]:
    phase = rng.choice(["PHASE2", "PHASE3"])
    sites = max(1, int(rng.lognormvariate(2.2 if phase == "PHASE2" else 3.6, 0.9)))
    rate = rng.lognormvariate(-0.4, 0.7)
    months = rng.uniform(8, 20) if phase == "PHASE2" else rng.uniform(14, 40)
    enrollment = max(10, int(sites * rate * months))
    start = date(2008, 1, 1) + timedelta(days=rng.randint(0, 5500))
    why: str | None = None
    if status == "TERMINATED":
        why = rng.choice(WHY_STOPPED)
        months *= rng.uniform(0.3, 0.8)
        enrollment = max(3, int(enrollment * rng.uniform(0.05, 0.5)))
    end = start + timedelta(days=int(months * 30.4375))
    min_age = rng.choice([18, 18, 18, 12, 40])
    max_age = rng.choice([65, 70, 75, 80, None])
    countries = rng.sample(COUNTRIES, min(sites, rng.randint(1, 6)))
    nct = f"SYN{index:08d}"
    status_module: dict[str, Any] = {
        "overallStatus": status,
        "startDateStruct": {"date": start.isoformat()},
        "primaryCompletionDateStruct": {"date": end.isoformat()},
        "completionDateStruct": {"date": end.isoformat()},
    }
    if why:
        status_module["whyStopped"] = why
    elig: dict[str, Any] = {
        "eligibilityCriteria": eligibility(rng, indication, min_age, max_age),
        "healthyVolunteers": False,
        "sex": "ALL",
        "minimumAge": f"{min_age} Years",
    }
    if max_age:
        elig["maximumAge"] = f"{max_age} Years"
    return {
        "queryIndication": indication,
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": f"Synthetic {CONDITIONS[indication]} study {nct}"},
            "statusModule": status_module,
            "sponsorCollaboratorsModule": {"leadSponsor": {"class": rng.choice(["INDUSTRY", "OTHER"])}},
            "conditionsModule": {"conditions": [CONDITIONS[indication]]},
            "designModule": {
                "studyType": "INTERVENTIONAL",
                "phases": [phase],
                "enrollmentInfo": {"count": enrollment, "type": "ACTUAL"},
            },
            "eligibilityModule": elig,
            "contactsLocationsModule": {
                "locations": [{"country": countries[i % len(countries)]} for i in range(sites)]
            },
        },
    }


def generate(out: Path, trials: int = 600, seed: int = 7) -> dict[str, dict[str, int]]:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, dict[str, int]] = {}
    index = 0
    plan = {"benchmark": trials // 3, "recruiting": max(1, trials // 20)}
    for dataset, per_indication in plan.items():
        counts[dataset] = {}
        with gzip.open(out / f"{dataset}_studies.jsonl.gz", "wt", encoding="utf-8") as fh:
            for indication in CONDITIONS:
                for _ in range(per_indication):
                    index += 1
                    if dataset == "recruiting":
                        status = "RECRUITING"
                    else:
                        status = "TERMINATED" if rng.random() < 0.12 else "COMPLETED"
                    fh.write(json.dumps(study(rng, index, indication, status), sort_keys=True) + "\n")
                counts[dataset][indication] = per_indication
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--trials", type=int, default=600)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    counts = generate(args.out, args.trials, args.seed)
    manifest = {"source": "synthetic", "seed": args.seed, "counts": counts}
    (args.out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
