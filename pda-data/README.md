# pda-data

Benchmark dataset pipeline for the **Protocol Design Advisor** demo (Jira MBA-3858).
A PySpark job reads a committed snapshot of public ClinicalTrials.gov records and writes
one Parquet row per trial with the features the API (`pda-api/`) benchmarks against.

All data is public registry data or synthetic. Only study-level fields are requested from the
API (no contacts, officials or investigators) and the job refuses to write a table whose
schema contains a person-level column.

## Run it

Requires Python 3.10+ and Java 17 (for Spark).

```bash
cd pda-data
python -m venv .venv && . .venv/bin/activate
make install      # editable install with dev tools
make test         # pytest on a local SparkSession (no network)
make run          # data/raw -> output/v1/{trial_features,recruiting_trials} + _MANIFEST.json
make check        # lint + type check + tests + pip-audit
make sbom         # CycloneDX SBOM -> sbom.json
```

## Data

| Path | What |
| --- | --- |
| `data/raw/benchmark_studies.jsonl.gz` | Completed and terminated interventional phase 2/3 trials, 700 most recently started per indication (asthma, COPD, type 2 diabetes) |
| `data/raw/recruiting_studies.jsonl.gz` | Currently recruiting trials for the same filters (competing trials per country) |
| `data/raw/MANIFEST.json` | Query, field list, fetch time and counts |

`make snapshot` refreshes the snapshot from `https://clinicaltrials.gov/api/v2/studies`.
If the API is unreachable it falls back to `scripts/generate_synthetic.py`, which writes
about 600 trials in the same API v2 JSON shape with `SYN`-prefixed IDs. The committed
snapshot is the real public one, so the fallback is exercised only by tests.

## Output (`output/v1/`)

The output folder is versioned by `pda_data.DATASET_VERSION`; bump it on a breaking schema change.

`trial_features`, one row per completed or terminated trial:

| Column | Notes |
| --- | --- |
| `nct_id`, `title`, `indication`, `phase`, `phase_group`, `overall_status`, `sponsor_class` | `phase_group` is 2 or 3; a phase 2/3 trial counts as 3 |
| `enrollment`, `enrollment_type` | Actual enrollment for finished trials |
| `site_count`, `country_count`, `countries` | From registered locations; `site_count` is null when none are listed |
| `start_date`, `primary_completion_date`, `duration_months` | Month-only dates resolve to the first of the month |
| `accrual_rate_per_site_month` | `enrollment / site_count / duration_months`; null without sites |
| `min_age_years`, `max_age_years`, `sex`, `healthy_volunteers` | Structured eligibility fields |
| `n_inclusion`, `n_exclusion`, `criteria_categories` | Parsed from the free-text criteria |
| `hba1c_*`, `bmi_*`, `fev1_pct_*`, `pack_years_*`, `egfr_*` (`_min`/`_max`) | Numeric bounds of the eligible range; null when not stated |
| `why_stopped`, `stop_category`, `low_accrual_terminated` | Category is one of `low_accrual`, `safety`, `efficacy_futility`, `funding`, `business`, `other`, `none` |

`recruiting_trials`, one row per recruiting trial and country, with the number of sites in that country.

## Cleaning rules

- A trial returned by more than one indication query is kept once.
- Rows must be interventional, phase 2 or 3, and completed or terminated.
- Rows without enrollment, a start date or a primary completion date, or with a
  non-positive duration, are dropped (8 of 2,059 unique trials in the current snapshot).
- Trials with no registered locations are kept with a null site count and accrual rate.

## Layout

```
src/pda_data/criteria.py   pure-Python eligibility and why-stopped parsing
src/pda_data/schema.py     explicit Spark schema for the raw API shape
src/pda_data/transform.py  DataFrame transforms
src/pda_data/job.py        entry point, Parquet writer, person-level column guard
scripts/                   snapshot fetch and synthetic fallback
tests/                     pytest with a session-scoped local SparkSession and a synthetic fixture
```

CI lives in `.github/workflows/pda-data.yml` and only runs for changes under `pda-data/`.
