# territory_kpis — weekly territory KPIs (UC1)

Modular, tested PySpark rewrite of `notebooks/territory_kpis.ipynb`. The notebook mixed pandas and Spark, used
hard-coded relative paths and `toPandas()` for the final joins; this job keeps the **exact same semantics** (parity
against the frozen notebook output is enforced in CI) but runs entirely on Spark DataFrames, is configurable, has
data-quality gates and a Databricks job definition.

## What it computes

One row per `territory_id` + `week` (`week` = the Monday, `DateType`), for every territory+week that has sales:

| column | definition |
|---|---|
| `region` | from `territories` |
| `visits`, `unique_hcps`, `f2f_visits` | count of visits, distinct `hcp_id`, visits with `channel == 'face_to_face'` (visit week = Monday of `visit_date`) |
| `f2f_share` | `f2f_visits / visits`, 4 dp |
| `avg_duration_min` | mean `duration_min`, 2 dp |
| `open_follow_ups` | follow-ups with `status == 'open'` due that week; `follow_ups` has no territory column, so territory comes from `reps` via `rep_id` |
| `rep_count` | reps per territory |
| `visits_per_rep` | `visits / rep_count`, 2 dp |
| `units`, `revenue_gbp` | `sum(units)`, `round(sum(revenue_gbp), 2)` from `weekly_sales` |
| `revenue_per_visit` | `revenue_gbp / visits` (2 dp) when `visits > 0`, else `0.0` |

Territory+weeks with sales but no visits / follow-ups get `0` (ints) and `0.0` (floats). Output is sorted by
`territory_id, week`.

> Rounding note: the notebook rounded `f2f_share`, `avg_duration_min`, `visits_per_rep` and `revenue_per_visit` in
> **pandas** (numpy round-half-to-even on the scaled double), while Spark's `F.round` is HALF_UP. On the repo data the
> two disagree on 30 values, so `transform.round_half_even` mirrors the numpy arithmetic (`bround(x * 10^n, 0) / 10^n`)
> and parity is exact (0 mismatches at tolerance 0). `revenue_gbp` was rounded in Spark in the notebook and still is.

## Module layout

```
pipelines/territory_kpis/
├── config.py     JobConfig dataclass: CLI args > TERRITORY_KPIS_* env vars > repo-relative defaults
├── extract.py    read_inputs(spark, input_dir) -> {territories, reps, visits, follow_ups, weekly_sales}
├── transform.py  pure DataFrame functions: week_start, aggregate_visits, aggregate_open_follow_ups,
│                 aggregate_sales, count_reps, assemble_kpis, build_territory_kpis
├── quality.py    CheckResult / QualityReport, check_* functions, run_quality_checks(df) raises DataQualityError
├── load.py       write_output(df, path): overwrite Parquet, create parent dirs
├── job.py        main(): SparkSession -> extract -> transform -> quality -> load
├── parity.py     compare job output with notebooks/expected_output/territory_kpis.parquet
├── tests/        pytest suite (local Spark, local[2], 4 shuffle partitions)
└── output/       job output (git-ignored)
```

## Run locally (from the repo root)

```bash
pip install -r requirements-dev.txt

# the job (defaults: --input-dir data, --output pipelines/territory_kpis/output/territory_kpis.parquet)
python pipelines/territory_kpis/job.py
python pipelines/territory_kpis/job.py --input-dir data --output /tmp/territory_kpis.parquet --master 'local[2]'
TERRITORY_KPIS_OUTPUT=/tmp/kpis.parquet python pipelines/territory_kpis/job.py   # env vars work too

# tests
pytest pipelines

# parity vs the frozen notebook output (runs the job first if the output is missing)
python pipelines/territory_kpis/parity.py            # ... prints "520 rows compared, 0 mismatches"
```

Options: `--input-dir`, `--output`, `--master`, `--shuffle-partitions`, `--min-rows`, `--max-rows`; the same names
as `TERRITORY_KPIS_INPUT_DIR`, `TERRITORY_KPIS_OUTPUT`, `TERRITORY_KPIS_SPARK_MASTER`, `TERRITORY_KPIS_SHUFFLE_PARTITIONS`,
`TERRITORY_KPIS_MIN_ROWS`, `TERRITORY_KPIS_MAX_ROWS`. Relative paths resolve against the repo root, never the CWD.

## Data-quality checks (`quality.py`)

Run after the transform and before the write; any failure raises `DataQualityError` with the full report, so nothing
is written downstream.

| check | rule |
|---|---|
| `schema` | all 14 output columns present with compatible types (string / date / integral / fractional) |
| `no_null_keys` | no nulls in `territory_id`, `week` |
| `unique_keys` | `(territory_id, week)` is unique |
| `row_count` | row count within `[--min-rows, --max-rows]` (default 100–5000; repo data gives 520) |

## Tests (`tests/`)

* `test_transform.py` — each transform function on tiny hand-built DataFrames, incl. non-Monday → Monday mapping,
  sales-without-visits → zeros and `revenue_per_visit = 0.0`, and the numpy-compatible rounding helper.
* `test_quality.py` — a passing and a failing case for every DQ check, plus `run_quality_checks` raising.
* `test_config.py` — repo-relative defaults, CLI and env overrides.
* `test_extract_load.py` — reading the six source tables, missing-file error, overwrite + directory creation.
* `test_job_e2e.py` — runs the whole job on `data/` and compares with `notebooks/expected_output/territory_kpis.parquet`.

## Parity (`parity.py`)

Aligns job output and notebook output on `territory_id` + `week` (both normalised to a date), checks row counts and key
sets, compares **every** column (numeric tolerance `1e-6`, exact for strings), prints a per-column summary and ends with
`N rows compared, M mismatches`; non-zero exit on any mismatch. CI runs it as the last step.

## Databricks deployment (shown, not run)

`jobs/territory_kpis.json` is a Jobs API 2.1 definition: a `spark_python_task` pointing at
`pipelines/territory_kpis/job.py` from this Git repo, a weekly schedule (`0 0 6 ? * MON`, UTC), a 1-worker job cluster
on an LTS runtime with auto-termination, `max_concurrent_runs: 1`, failure notifications, and a dependent
`parity_check` task. No Databricks account is needed for this demo; to deploy it you would run:

```bash
databricks jobs create --json @jobs/territory_kpis.json        # first time
databricks jobs reset --job-id <id> --json @jobs/territory_kpis.json   # subsequent updates
```

On Databricks `SparkSession.builder.getOrCreate()` returns the cluster session, so the `--master` option is ignored;
point `--input-dir` / `--output` at Unity Catalog volumes (or DBFS) instead of the repo `data/` folder.
