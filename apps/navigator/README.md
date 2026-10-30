# Field Force Navigator (UC4)

The UC4 product scaffold in the GSK Scale AI demo kit: a FastAPI backend that serves the curated UC1 tables
(`data/*.parquet`, built by `pipelines/territory_kpis`) and a React/Vite frontend that will grow into the
rep-facing Navigator. UC1 built the data, UC4 builds the product, UC3 runs it. Synthetic data only.

```
apps/navigator/
├── backend/            FastAPI (pydantic v2), package `app`
│   ├── app/
│   │   ├── main.py     app = FastAPI(...), lifespan loads the tables, CORS for the Vite dev server
│   │   ├── server.py   container entrypoint: /api -> main:app, / -> built SPA, /health
│   │   ├── data.py     load_tables(): data/*.parquet -> in-memory pandas DataFrames (DataStore)
│   │   └── models.py   Health, Rep, Territory response models
│   ├── tests/          pytest + TestClient (conftest.py puts backend/ on sys.path)
│   └── requirements.txt
├── Dockerfile          multi-stage image (node:20-alpine build -> python:3.11-slim), see "Run the container"
└── frontend/           React 18 + Vite 5 + TypeScript, vitest + Testing Library, ESLint 9 flat config
    ├── src/App.tsx     placeholder page: calls /health, lists /reps
    ├── src/api.ts      typed fetch helpers (all calls go through /api)
    └── vite.config.ts  dev proxy /api -> VITE_API_BASE (default http://localhost:8000)
```

## Data

At startup the backend reads `hcps`, `visits`, `follow_ups`, `reps`, `territories` and `weekly_sales` from the
data directory with pandas + pyarrow and keeps them in memory. The directory defaults to `<repo root>/data`
(resolved relative to the package, not the CWD) and can be overridden with `NAVIGATOR_DATA_DIR` (absolute, or
relative to the repo root).

The *as-of date* ("today" for days-since-last-visit and scoring) is the latest `visit_date` in the data,
2025-09-29, unless `NAVIGATOR_AS_OF_DATE=YYYY-MM-DD` is set; `GET /health` reports it as `as_of`.

## Run the backend

```bash
pip install -r apps/navigator/backend/requirements.txt
uvicorn app.main:app --reload --app-dir apps/navigator/backend          # http://127.0.0.1:8000/docs
```

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/health` | `{"status": "ok", "version", "data_dir", "row_counts": {table: rows}}` |
| GET | `/reps` | reps (`rep_id`, `rep_name`, `territory_id`, `region`, `hire_date`), region joined from `territories` |
| GET | `/territories` | territories (`territory_id`, `territory_name`, `region`) |
| GET | `/reps/{rep_id}/hcps` | `{rep, territory, as_of, count, hcps: HcpView[]}` for the rep's territory, scored and sorted (score desc, name asc); filters `specialty`, `segment` (A/B/C), `min_days_since_last_visit` (never-visited rows match), `q` (case-insensitive name search), `as_of` (YYYY-MM-DD); 404 unknown rep |
| GET | `/scoring/rules` | scoring rules in effect |
| GET | `/scoring/explain?segment=A&days_since_last_visit=45&open_follow_ups=1` | `{score, reason, factors}` for arbitrary inputs |
| GET | `/reps/{rep_id}/plan?as_of=` | the rep's weekly `Plan` (`week_start`, `max_visits_per_day`, `total_visits`, `days[]` with `count`/`capacity`/`visits[]`, `warnings[]`); 404 unknown rep |
| POST | `/reps/{rep_id}/plan/visits` body `{"hcp_id", "day": "Mon".."Fri"}` | `201 Plan`; `409` when the day is full (`"Tuesday already has 6 visits (max 6)"`), `422` bad day or HCP outside the rep's territory, `404` unknown rep/HCP |
| DELETE | `/reps/{rep_id}/plan/visits/{visit_id}` | `Plan` without that visit; 404 if absent |
| DELETE | `/reps/{rep_id}/plan` | the emptied `Plan` |

Plans are held in process memory per rep (`app/plans.py`, `PlanStore`) and rebuilt from the scored HCP view on every
read, so scores and warnings follow the as-of date. Warnings: `overdue_segment_a` (Segment A HCP overdue and not
planned anywhere this week) and `duplicate` (HCP planned more than once; allowed, not blocked).

| Variable | Default | Effect |
| --- | --- | --- |
| `NAVIGATOR_MAX_VISITS_PER_DAY` | `6` | per-day capacity; the (n+1)th add is rejected with 409 |
| `NAVIGATOR_OVERDUE_DAYS` | `30` | a Segment A HCP with more days since the last visit (or never visited) raises an `overdue_segment_a` warning |

CORS is enabled for `http://localhost:5173` / `http://127.0.0.1:5173`; override with a comma-separated
`NAVIGATOR_CORS_ORIGINS`.

### Scoring rules

`GET /scoring/rules` returns the rules in effect (`app/scoring.py`, `ScoringRules`); `/scoring/explain` scores
arbitrary inputs. Defaults: `segment_weights` `A=40, B=25, C=10`, `points_per_day` 1, `days_cap` 40 (never visited =
cap), `open_follow_up_bonus` 20, `recent_visit_days` 7 (visited within 7 days scores 0), `max_score` 100. Override
any subset at startup with `NAVIGATOR_SCORING_RULES` (a JSON object, e.g. `{"days_cap": 60, "segment_weights":
{"A": 50, "B": 25, "C": 5}}`) or `NAVIGATOR_SCORING_RULES_FILE` (path to a JSON file); invalid values fail fast.

### Environment variables

| Variable | Default | Used by |
| --- | --- | --- |
| `NAVIGATOR_DATA_DIR` | `<repo root>/data` | `app/data.py`, location of the six parquet tables |
| `NAVIGATOR_AS_OF_DATE` | latest `visit_date` (2025-09-29) | reference date for days since last visit |
| `NAVIGATOR_STATIC_DIR` | `apps/navigator/frontend/dist` | `app/server.py`, built SPA served at `/` |
| `NAVIGATOR_CORS_ORIGINS` | Vite dev server origins | `app/main.py` |
| `NAVIGATOR_MAX_VISITS_PER_DAY`, `NAVIGATOR_OVERDUE_DAYS` | `6`, `30` | `app/plans.py` |
| `NAVIGATOR_SCORING_RULES`, `NAVIGATOR_SCORING_RULES_FILE` | defaults above | `app/scoring.py` |

## Run the container

One image serves the API under `/api`, the built frontend at `/` and `/health` on port 8000 with the curated tables
baked in (`app/server.py`). Build from the **repo root** so `data/*.parquet` is in the build context:

```bash
docker build -f apps/navigator/Dockerfile -t navigator .
docker run --rm -p 8000:8000 navigator
curl -s localhost:8000/health            # {"status":"ok",...,"as_of":"2025-09-29",...}
curl -s localhost:8000/api/reps | head -c 200
open http://localhost:8000               # the SPA; API docs at /api/docs
```

The image sets `NAVIGATOR_DATA_DIR=/srv/data` and `NAVIGATOR_STATIC_DIR=/srv/static`; pass `-e NAVIGATOR_AS_OF_DATE=…`
or any variable from the table above to `docker run` to override. `apps/navigator/Dockerfile.dockerignore` keeps the
build context to the backend, the frontend sources and the parquet files. Without a frontend build (`uvicorn
app.server:app` locally before `npm run build`), `/` returns a JSON pointer at `/api/docs` instead of failing.

## Run the frontend

Requires Node 20.

```bash
cd apps/navigator/frontend
npm ci
npm run dev            # http://localhost:5173, proxies /api/* to the backend
```

Set `VITE_API_BASE` (see `.env.example`) if the backend is not on `http://localhost:8000`.

## Test and lint

From the repo root (ruff + pytest config live in `pyproject.toml`):

```bash
ruff check .
pytest apps/navigator/backend
pytest apps/navigator/backend --cov=navigator_app.scoring --cov-report=term-missing --cov-fail-under=90   # NFR-1
pytest apps/navigator/backend/tests/test_perf.py -s   # NFR-3: prints the 300-HCP timings (p95 must be < 1 s)
```

`tests/conftest.py` loads the backend package under the alias `navigator_app` (the `services/supply_api` package is
also called `app`), so coverage targets and test imports use `navigator_app.…`.

Frontend:

```bash
cd apps/navigator/frontend
npm run lint
npm test -- --run       # includes src/a11y.test.tsx (NFR-4: tab order, accessible names, aria-live / role=alert)
npm run build
```

## CI

`.github/workflows/ci.yml` runs three jobs on every PR, all required:

| Job | What it runs |
| --- | --- |
| `python` | `ruff check .`, `pytest` across `data`, `pipelines`, `services`, `apps` (installs `apps/*/backend/requirements.txt` automatically), then the scoring coverage gate `pytest apps/navigator/backend --cov=navigator_app.scoring --cov-fail-under=90` |
| `navigator-frontend` | Node 20, `npm ci`, `npm run lint`, `npm test -- --run`, `npm run build` |
| `navigator-container` | `docker build -f apps/navigator/Dockerfile`, `docker run -p 8000:8000`, waits for `/health`, then checks `/health`, `/api/reps`, `/api/reps/R001/hcps` (contains `"T001"`) and `/` (contains `<div id="root">`); prints `docker logs` on failure |
