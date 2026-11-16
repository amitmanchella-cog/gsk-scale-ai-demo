"""Fetch the benchmark snapshot from the public ClinicalTrials.gov API v2.

Only study-level, non-personal fields are requested (no contacts, officials or
investigators). The result is committed under ``data/raw`` so that the pipeline
and its tests never call the network.

Usage: python scripts/fetch_snapshot.py [--out data/raw] [--max-per-indication 700]
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_URL = "https://clinicaltrials.gov/api/v2/studies"
INDICATIONS = {
    "asthma": "asthma",
    "copd": "chronic obstructive pulmonary disease",
    "type_2_diabetes": "type 2 diabetes mellitus",
}
FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "WhyStopped",
    "StartDate",
    "PrimaryCompletionDate",
    "CompletionDate",
    "EnrollmentCount",
    "EnrollmentType",
    "Phase",
    "StudyType",
    "Condition",
    "EligibilityCriteria",
    "MinimumAge",
    "MaximumAge",
    "Sex",
    "HealthyVolunteers",
    "LocationCountry",
    "LeadSponsorClass",
]
ADVANCED = "AREA[StudyType]INTERVENTIONAL AND AREA[Phase](PHASE2 OR PHASE3)"
DATASETS = {
    "benchmark": "COMPLETED|TERMINATED",
    "recruiting": "RECRUITING",
}


def fetch(condition: str, statuses: str, limit: int) -> list[dict[str, Any]]:
    studies: list[dict[str, Any]] = []
    token: str | None = None
    while len(studies) < limit:
        params = {
            "query.cond": condition,
            "filter.overallStatus": statuses,
            "filter.advanced": ADVANCED,
            "fields": ",".join(FIELDS),
            "sort": "StartDate:desc",
            "pageSize": "200",
        }
        if token:
            params["pageToken"] = token
        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "pda-data-snapshot/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https URL
            page = json.load(resp)
        studies.extend(page.get("studies", []))
        token = page.get("nextPageToken")
        if not token:
            break
        time.sleep(0.3)
    return studies[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-per-indication", type=int, default=700)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        fetch(INDICATIONS["asthma"], DATASETS["benchmark"], 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        from generate_synthetic import generate

        print(f"API unreachable ({exc}); writing the synthetic fallback instead", file=sys.stderr)
        fallback = {"source": "synthetic", "seed": 7, "counts": generate(args.out)}
        (args.out / "MANIFEST.json").write_text(json.dumps(fallback, indent=2) + "\n")
        return

    manifest: dict[str, Any] = {
        "source": API_URL,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filter.advanced": ADVANCED,
        "fields": FIELDS,
        "sort": "StartDate:desc",
        "max_per_indication": args.max_per_indication,
        "files": {},
    }
    # Each file is written next to the snapshot and swapped in only once every fetch has succeeded,
    # so a failed refresh leaves the previous snapshot intact.
    partials: dict[Path, Path] = {}
    for dataset, statuses in DATASETS.items():
        path = args.out / f"{dataset}_studies.jsonl.gz"
        partials[path] = path.with_name(path.name + ".partial")
        counts: dict[str, int] = {}
        with gzip.open(partials[path], "wt", encoding="utf-8") as fh:
            for key, condition in INDICATIONS.items():
                studies = fetch(condition, statuses, args.max_per_indication)
                counts[key] = len(studies)
                for study in studies:
                    # Tag the query that returned the study; the API shape is otherwise untouched.
                    fh.write(json.dumps({"queryIndication": key, **study}, sort_keys=True) + "\n")
                print(f"{dataset}/{key}: {len(studies)} studies")
        manifest["files"][path.name] = {"filter.overallStatus": statuses, "counts": counts}
    for path, partial in partials.items():
        partial.replace(path)
    (args.out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
