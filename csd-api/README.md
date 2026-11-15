# csd-api

FastAPI service for the computable study design core. It exposes the operations and queries
of [`csd-core`](../csd-core) over HTTP and stores versions in SQL. The UI
([`csd-web`](../csd-web)), the tests and any agents all call this same API.

All data is synthetic. No person-level data is stored.

> In this demo each "repo" is a top-level folder of one repository, so `csd-core` is
> installed from the sibling folder instead of from a git URL.

## Run

```bash
cd csd-api
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ../csd-core -e ".[dev]"
uvicorn csd_api.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive OpenAPI page. On first start the
synthetic reference study is seeded as study `asthma-ref`.

## Endpoints

| Method and path | Purpose |
|---|---|
| `GET /health` | Liveness and study count |
| `GET /operation-types` | Names of the operation types the core supports |
| `GET /studies`, `GET /studies/{study_id}` | Study summaries (root and head version IDs) |
| `POST /studies` | Create a fresh copy of the reference study (a sandbox; used by the e2e tests) |
| `GET /studies/{study_id}/versions` | Version timeline (no graphs) |
| `GET /studies/{study_id}/branches` | Branches and their heads |
| `GET /versions/{version_id}` | A version: graph, operation, parent and findings |
| `POST /versions/{version_id}/operations` | Apply a typed operation to a branch head; returns the new version (201) |
| `POST /versions/{version_id}/operations?branch=<name>` | The same, extending the named branch (its first operation is posted to its base version) |
| `POST /versions/{version_id}/branches` | Start a branch `{"name": ...}` from any version, head or not (201). No version is created |
| `GET /versions/{version_id}/score` | Visit count, total patient time in minutes and cost proxy |
| `GET /compare?left=<id>&right=<id>` | Two versions side by side: scores, findings, delta (right minus left) and element changes |
| `GET /versions/{id}/drafts` | ICH M11 sections 3, 5 and 8 drafted from the graph; every sentence lists its graph element IDs |
| `GET /versions/{id}/drafts/{section}` | One drafted section: `3`, `5` or `8` |
| `GET /versions/{version_id}/findings` | Findings of a version |
| `GET /versions/{version_id}/schedule` | Schedule-of-activities grid |

Errors: `404` unknown ID, `409` the version is not a branch head, `422` the operation is
malformed, not applicable, or would make the study structurally invalid. In all three cases
no version is created.

### Flagship scenario

```bash
ROOT=$(curl -s localhost:8000/studies/asthma-ref | jq -r .root_version_id)
V1=$(curl -s -X POST localhost:8000/versions/$ROOT/operations -H 'content-type: application/json' \
  -d '{"type":"MoveVisit","visit_id":"V-W12","day":99}' | jq -r .id)
curl -s localhost:8000/versions/$V1/findings | jq '.findings[].id'   # unmet_endpoint_timepoint:EP-FEV1
V2=$(curl -s -X POST localhost:8000/versions/$V1/operations -H 'content-type: application/json' \
  -d '{"type":"ChangeEndpointTiming","endpoint_id":"EP-FEV1","week":14}' | jq -r .id)
curl -s localhost:8000/versions/$V2/findings | jq .count             # 0
```

## Storage

`csd_api.sql_store.SqlVersionStore` implements the core's `VersionStore` port with SQLAlchemy
Core and portable column types. Versions are immutable JSON documents.

| Setting | Default | Notes |
|---|---|---|
| `CSD_DATABASE_URL` | `sqlite:///./csd.db` | For PostgreSQL: `pip install -e ".[postgres]"` and set `postgresql+psycopg://user:pass@host/db`. Only SQLite is exercised by the tests. |

Tables are created on start (`csd_versions`, `csd_branches`). Delete `csd.db` to reset the demo.

## Checks

```bash
ruff check . && ruff format --check .
mypy
pytest            # unit + Hypothesis property tests, coverage threshold 90%
pip-audit --skip-editable
```

## Docker

The image needs `csd-core`, so build from the repository root:

```bash
docker build -f csd-api/Dockerfile -t csd-api .
docker run -p 8000:8000 csd-api
```

`csd-web/docker-compose.yml` starts this API together with the UI.
