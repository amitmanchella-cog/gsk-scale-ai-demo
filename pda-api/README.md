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
src/pda_api/routers/       HTTP endpoints
samples/                   three synthetic draft protocols
```

CI lives in `.github/workflows/pda-api.yml` and only runs for changes under `pda-api/`.
