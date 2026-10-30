# Field Force Navigator (UC4)

The UC4 product scaffold in the GSK Scale AI demo kit: a FastAPI backend that serves the curated UC1 tables
(`data/*.parquet`, built by `pipelines/territory_kpis`) and a React/Vite frontend that will grow into the
rep-facing Navigator. UC1 built the data, UC4 builds the product, UC3 runs it. Synthetic data only.

```
apps/navigator/
├── backend/            FastAPI (pydantic v2), package `app`
│   ├── app/
│   │   ├── main.py     app = FastAPI(...), lifespan loads the tables, CORS for the Vite dev server
│   │   ├── data.py     load_tables(): data/*.parquet -> in-memory pandas DataFrames (DataStore)
│   │   └── models.py   Health, Rep, Territory response models
│   ├── tests/          pytest + TestClient (conftest.py puts backend/ on sys.path)
│   └── requirements.txt
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
```

Frontend:

```bash
cd apps/navigator/frontend
npm run lint
npm test -- --run
npm run build
```

## CI

`.github/workflows/ci.yml` has two jobs: the existing `python` job (ruff + pytest across `data`, `pipelines`,
`services`, `apps`; it installs `apps/*/backend/requirements.txt` automatically) and `navigator-frontend`
(Node 20, `npm ci`, `npm run lint`, `npm test -- --run`, `npm run build`).
