# pda-api

API for the **Protocol Design Advisor** demo. It extracts the structured design from a draft
clinical-trial protocol and benchmarks it against public ClinicalTrials.gov trials prepared by
`pda-data/`.

FastAPI on Python 3.11, SQLAlchemy async, SQLite for the demo. Everything runs offline: the
language model sits behind `pda_api.providers.LLMProvider` and the only implementation shipped is
the deterministic, rule-based `MockProvider`. Every number the API returns is computed by code
from the benchmark dataset.

## Run it

```bash
cd pda-api
python3.11 -m venv .venv && . .venv/bin/activate
make install
make run            # http://localhost:8000/docs
make test           # pytest, no network
make check          # lint + type check + tests + pip-audit
```

Try it with a bundled synthetic protocol:

```bash
curl -F file=@samples/t2d_phase3_weak.txt http://localhost:8000/api/protocols
curl http://localhost:8000/api/protocols/<id>/assessment
```

## Endpoints

| Method and path | What it does |
| --- | --- |
| `POST /api/protocols` | Upload a `.txt` or `.docx` draft. Returns the extracted design: indication, phase, population, target enrollment, planned countries, site count and each eligibility criterion as its own item |
| `GET /api/protocols/{id}` | The stored design |
| `GET /api/protocols/{id}/assessment?similar=40` | The 20 to 50 most similar benchmark trials (same indication and phase, nearest by enrollment, age window and criteria mix) and a 0-100 restrictiveness score per criterion with the trials that drive it |
| `GET /api/protocols/{id}/competing-trials` | Recruiting trials of the same indication in each planned country |
| `GET /api/protocols/{id}/forecast?seed=` | P50 and P90 months to full enrollment from a seeded Monte Carlo simulation, and the risk of termination for low accrual with the trial IDs behind it |
| `GET /api/protocols/{id}/suggestions` | Design changes that shorten the forecast. Each cites at least 5 benchmark trials and passed the evidence validator |
| `POST /api/protocols/{id}/what-if` | Body `{"changes": [...]}`. Applies the changes to a copy of the design and returns baseline and scenario forecasts. The stored protocol is not modified |
| `GET /api/protocols/{id}/report?format=html\|pdf\|json&accept=S1&accept=S4` | The design-review report: design, criterion scores, forecast (draft and with the accepted changes), termination risk, accepted changes and every cited trial. `accept` takes suggestion IDs and may be repeated |
| `GET /api/samples`, `GET /api/samples/{key}` | The three synthetic sample protocols in `samples/` (`t2d_phase3_weak` is deliberately weak) |
| `GET /api/health` | Status, provider and benchmark size |

### How a criterion is scored

- **range** (age, HbA1c, BMI, FEV1, pack-years, eGFR): the share of similar trials whose eligible
  range is wider than the draft's. Tightening a range raises the score.
- **prevalence** (pregnancy, malignancy, prior therapy and other keyword categories): the share of
  similar trials with no comparable criterion, so a rarely used criterion scores high.
- **burden** (criteria that match no category): the share of similar trials with fewer criteria
  in total than the draft.

70 and above is flagged high, 40 to 69 moderate.

### How the forecast works (MBA-3860)

`forecast.py` runs 2,000 simulations with a fixed seed (`numpy` generator, default seed 20260115),
so the same design always gives the same P50 and P90. In each simulation:

1. One benchmark accrual rate (patients per site per month) is drawn from the similar trials. If
   fewer than 10 of them have a usable rate, the draw comes from the indication and phase
   percentiles in the pda-data `accrual_benchmarks` table.
2. Every site gets that rate times its own gamma multiplier (mean 1), and its own activation
   month drawn uniformly over the ramp window. A site enrolls nothing before it opens. The window
   is 6 months, plus 1 month per 25 sites above 25, at most 18. `ramp=0` gives flat accrual.
3. The rate is multiplied by an eligibility factor: for each numeric criterion, the share of the
   similar trials' median window that the draft still allows; the factors are combined as a
   geometric mean and floored at 0.25.
4. The result is the month in which cumulative enrollment reaches the target.

Modelling assumptions, not measurements: the ramp shape (ClinicalTrials.gov has no site activation
dates), the site-to-site spread, and the eligibility factor (it assumes patients are spread evenly
across a window). The default was stated in the clarifying comment on MBA-3860.

**Termination risk** is the share of similar trials terminated for low accrual, smoothed towards
the indication and phase share (weighted as 20 extra trials, so a sample with no such termination
does not report zero), then multiplied by forecast P50 over the similar trials' median duration,
limited to 0.5-4.

### Suggestions and the evidence validator

`suggestions.py` proposes two kinds of change: relax a numeric criterion scored 70 or more to the
median window of similar trials, and add sites in the countries where benchmark trials accrued
fastest (pda-data `country_accrual`). Every number in a suggestion is produced by `metrics_for`
from the dataset and the seeded forecast; the LLM provider is not involved. `validate` recomputes
them and rejects a suggestion that cites fewer than 5 benchmark trials, cites a trial that is not
in the dataset or does not support the change, carries an evidence value that differs from the
recomputation, or has any number in its text that is not one of the computed values. Suggestions
that fail, or that do not shorten the forecast, are not returned.

### Design-review report (MBA-3863)

- `build_report` collects the values the other endpoints return; `blocks` turns them into
  headings, paragraphs and tables; `render_html` and `render_pdf` print those blocks. Neither
  renderer computes a number, so the two formats cannot disagree with each other or with the API.
- Changes are accepted by suggestion ID, so a report can only contain changes that passed the
  evidence validator. An unknown ID returns 422.
- The HTML is one file with inline styles, no scripts and no external assets. The PDF is drawn
  with ReportLab and its built-in fonts, which cover Windows-1252; any other character in a
  trial title prints as `?`.
- The report is generated on request and not stored.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./pda.db` | PostgreSQL: `pip install -e ".[postgres]"` and use `postgresql+asyncpg://user:pass@host/db` |
| `PDA_BENCHMARK_DIR` | `tests/fixtures/benchmark/v1` | Folder with `trial_features.parquet` and `recruiting_trials.parquet`. A Spark output folder from `pda-data` also works |
| `PDA_LLM_PROVIDER` | `mock` | Only `mock` is shipped |
| `PDA_CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma separated |

## Data and privacy

- `tests/fixtures/benchmark/v1/` is a committed copy of the Parquet that `pda-data` produces from
  its public snapshot. `make sync-benchmark` refreshes it from a local `pda-data` run.
- Only the extracted design is stored. The uploaded document text is not persisted.
- `tests/test_privacy.py` scans the schema and the stored rows and fails on any person-level
  column or value (name, email, date of birth, patient ID, phone).
- `tests/fixtures/labelled/eligibility.json` holds 10 hand-labelled eligibility texts; the
  extraction test requires field-level F1 of at least 0.85.

## Layout

```
src/pda_api/providers/     LLMProvider interface and the rule-based MockProvider
src/pda_api/criteria.py    eligibility parsing, vendored from pda-data so both sides parse alike
src/pda_api/benchmark.py   Parquet loader
src/pda_api/similarity.py  similar-trial search
src/pda_api/restrictiveness.py, competing.py   scoring and competing trials
src/pda_api/report.py      design-review report model, HTML and PDF renderers
src/pda_api/routers/       HTTP endpoints
samples/                   three synthetic draft protocols
```

CI lives in `.github/workflows/pda-api.yml` and only runs for changes under `pda-api/`.
