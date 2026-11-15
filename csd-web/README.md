# csd-web

React + TypeScript (Vite) UI for the computable study design core. It talks only to
[`csd-api`](../csd-api); there is no mock API. All data is synthetic.

Views in this version:

- **Schedule of activities** grid (activities by visit). Edit a visit's study day to move it;
  click a cell to schedule or unschedule an activity.
- **Graph**: the intent graph (objectives, endpoints, design activities, arms) linked to the
  plan graph (activities, visits, operational standards), drawn with React Flow.
- **Findings** panel: the intent-vs-plan warnings of the version on screen. Click a finding to
  highlight its graph elements in the grid and the graph.
- **Version timeline**: every operation is its own immutable version. Older versions open read only.
- **Endpoints** panel (change an endpoint's timing) and a form that can apply any operation
  type the API supports.

## Run it

With Docker (API and UI together):

```bash
cd csd-web
docker compose up --build
# UI http://localhost:8080 · API docs http://localhost:8000/docs
```

Without Docker (Python 3.11 and Node 20 or newer):

```bash
# terminal 1, from the repository root: the API on :8000
python -m venv .venv && . .venv/bin/activate
pip install -e ./csd-core -e ./csd-api
uvicorn csd_api.main:app --port 8000

# terminal 2: the UI on :5173, proxying /api to the API
cd csd-web
npm ci
npm run dev
```

The reference study opens at `/`. `/?study=<id>` opens another study; create a fresh copy of
the reference study with `curl -X POST localhost:8000/studies`.

Set `CSD_API_URL` if the API is not on `http://localhost:8000`.

## The flagship scenario, by hand

1. In the grid, change **Week 12** from Day `85` to `99` and press Enter. The timeline gains
   `v1` and the findings panel shows one *Unmet endpoint timepoint* warning on the FEV1 primary endpoint.
2. In **Endpoints**, set the FEV1 week to `14` and press **Change timing**. The timeline gains
   `v2` and the findings panel is back to zero.
3. Click `v0` and `v1` in the timeline: both are unchanged.

## Branches and compare, by hand

1. In **Branches**, type `fewer-visits` and press **Create branch**. The branch starts from
   the version on screen (any version, head or not) and no version is created.
2. Press **Remove** under Week 4. The score bar drops from 7 visits, 640 min, 2160 to
   6 visits, 550 min, 1940.
3. Switch **Viewing** back to `main`, create `acq5-primary`, and press **Make primary** on
   the ACQ-5 endpoint.
4. Open **Compare branches** and pick the two branches: the scores render side by side
   with the difference, each side's findings, and the graph elements that differ.

## Checks

```bash
npm run lint        # eslint
npm run typecheck   # tsc
npm test            # vitest with coverage (80% line threshold)
npm run audit       # npm audit of runtime dependencies
```

### End-to-end tests (Playwright)

The suite starts the **real API** (on a throwaway SQLite file) and a production build of the
UI, and every test creates its own study through the API. It runs on four projects:
`chromium`, `firefox`, `webkit` (Safari's engine) and `webkit-ipad` (WebKit with the
iPad Pro 11 profile, which exercises the tablet layout).

```bash
npx playwright install --with-deps
CSD_PYTHON=../.venv/bin/python npm run e2e      # CSD_PYTHON: an interpreter with csd-api installed
npx playwright show-report                       # HTML report with video, trace and screenshots
```

Video, trace and screenshots are recorded for every test (`test-results/`), and the HTML
report is written to `playwright-report/`. CI uploads both as artifacts.
