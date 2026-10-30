# CCR-NAV-001 — Change Control Record: introduce Field Force Navigator v0.1 scaffold (MBA-3680 / PR #8)

> Synthetic, written for the GSK Scale AI demo (UC2 GxP controlled documentation). No real GSK systems, people or
> data. AI-drafted draft for QA review; not approved.

| Field | Value |
|---|---|
| Document ID | CCR-NAV-001 |
| Document type | CCR |
| Version | 0.1 DRAFT |
| Status | Draft |
| System | Field Force Navigator (`apps/navigator`) — SYS code NAV |
| GAMP 5 category | 5 (custom application) — per `docs/gxp/ESTATE_MAP.md` §2 |
| GxP impact | Indirect (HCP interaction records, compliance-relevant) — justified in §10 |
| Change reference | Jira [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680); PR [#8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8), merge commit `20e748e39c98d163c6d1f6fc2398254b3916d3f4` |
| Author | Devin (AI-drafted, playbook GxP controlled document from change) — session https://devin-gtm.devinenterprise.com/sessions/dbf21b4a44154051a6d06e3a3071769a |
| Effective date | _set by QA on approval_ |
| Governing SOPs | SOP-IT-002 (v3.1), SOP-QA-001 (v2.0) |

## Approvals

| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | Devin (AI-drafted, playbook GxP controlled document from change) | Authored and technically accurate | |
| System Owner | | Change approved for release; content fit for intended use | |
| Technical Reviewer | | Evidence matches the code, tests and CI at `20e748e` | |
| Quality Assurance | | Complies with SOP-IT-002 / SOP-QA-001; CCR closed | |

> Electronic signatures follow 21 CFR Part 11 §11.50/§11.70 (name, date/time, meaning) in the system of record.
> In this demo the system of record is the Git PR: approval = PR review "Approve" by the named role. The AI author
> does not sign or approve (SOP-QA-001 §3).

## 1. Change summary

| Field | Value |
|---|---|
| Change title | Introduce Field Force Navigator v0.1 scaffold (FastAPI backend + React/Vite placeholder frontend) into the validated estate |
| Change type | Normal — new validated system (SOP-IT-002 §5.1, §6 row "New validated system / major version"). Recorded retrospectively: see deviation in §4 K09 |
| Requested by / date | Code change: PR #8 opened by `devin-ai-integration[bot]` 2026-10-30 06:59 UTC. Change ticket: MBA-3680 raised by "Devin" 2026-10-30 13:58 UTC (06:58 PDT), i.e. after the merge |
| Ticket | [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680) — "UC2 GxP change control: Field Force Navigator v0.1 scaffold (PR #8)", Task, labels `gsk-demo`, `uc2-gxp` |
| Pull request(s) and merge commit | [PR #8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8) "UC4: scaffold Field Force Navigator (FastAPI + React/Vite)", head `53cf99e`, merged 2026-10-30 07:06 UTC by `devin-ai-integration[bot]` → merge commit `20e748e39c98d163c6d1f6fc2398254b3916d3f4` on `main` (parent `7988df6`) |
| Release / version | Navigator 0.1.0 (`apps/navigator/backend/app/__init__.py` `__version__ = "0.1.0"`; `apps/navigator/frontend/package.json` `"version": "0.1.0"`). No release tag |
| Environments | CI (GitHub Actions, PR + push to `main`) → `main`. No deployment environment in this change |

## 2. Description and justification (what changes and why)

**What.** PR #8 adds a new application, `apps/navigator`, as built at `20e748e`:

- **Backend** (FastAPI, pydantic v2, package `app`): at start-up (`lifespan` in `app/main.py`) loads the six curated
  UC1 tables `hcps`, `visits`, `follow_ups`, `reps`, `territories`, `weekly_sales` from `data/*.parquet` into memory
  (`app/data.py` `load_tables()` → `DataStore`). The data directory resolves as explicit argument >
  `NAVIGATOR_DATA_DIR` > `<repo root>/data` (repo-relative, not CWD); a missing directory or table raises
  `FileNotFoundError` (fail closed). Three read-only endpoints:
  `GET /health` (status, version, data_dir, per-table row counts), `GET /reps` (reps sorted by `rep_id`, `region`
  left-joined from `territories`), `GET /territories` (sorted by `territory_id`). CORS allows
  `http://localhost:5173` / `http://127.0.0.1:5173` by default, overridable with `NAVIGATOR_CORS_ORIGINS`.
- **Frontend** (React 18, Vite 5, TypeScript 5.6, vitest 2): placeholder page `src/App.tsx` titled
  "Field Force Navigator" that calls `/api/health` and `/api/reps` (`src/api.ts`), shows API status/row counts and a
  reps table, or "API unreachable: …" on error.
- **CI**: new job `navigator-frontend` ("Navigator frontend (lint, test, build)") in `.github/workflows/ci.yml`
  (Node 20, `npm ci`, `npm run lint`, `npm test -- --run`, `npm run build`). The existing `python` job is unchanged
  and already picks up `apps/*/backend/requirements.txt` and `pytest` testpath `apps`.

**Why.** Starts the Territory Call Planner product defined in `docs/uc4/PRD.md` on top of the curated UC1 data
(`pipelines/territory_kpis` output), replacing spreadsheet-based visit planning (synthetic scenario). MBA-3680 brings
the new system under change control so it enters the validated estate (`ESTATE_MAP.md` §4: all NAV documents missing).

**Not in this change.** None of the three PRD features (Territory HCP list, Visit priority score, Weekly plan builder
incl. CSV export) nor the PRD NFRs on scoring coverage, container build, HCP-list performance and keyboard
accessibility are implemented at `20e748e`; they are listed in §9 with status `Not implemented in this change` and a
`GAP —` note. PRD out-of-scope items (CRM integration, real HCP data/PII, SSO, mobile, route optimisation, GenAI) are
also absent.

## 3. Scope of change (files / components touched — from the diff)

`git diff --shortstat 7988df6 20e748e`: 27 files changed, 5426 insertions, 0 deletions (additive only).

| Component | Files (status, lines) |
|---|---|
| Backend app | `apps/navigator/backend/app/__init__.py` (A, +3), `app/data.py` (A, +55), `app/main.py` (A, +69), `app/models.py` (A, +26) |
| Backend deps | `apps/navigator/backend/requirements.txt` (A, +7): `fastapi>=0.110`, `uvicorn>=0.29`, `pandas>=2.0`, `pyarrow>=14`, `pydantic>=2.6`, `httpx>=0.27`, `pytest>=8` |
| Backend tests | `apps/navigator/backend/tests/conftest.py` (A, +40), `tests/test_data.py` (A, +32, 5 tests), `tests/test_endpoints.py` (A, +46, 4 tests) |
| Frontend source | `apps/navigator/frontend/src/App.tsx` (A, +72), `src/api.ts` (A, +27), `src/main.tsx` (A, +10), `src/index.css` (A, +69), `src/vite-env.d.ts` (A, +1), `index.html` (A, +12) |
| Frontend tests | `apps/navigator/frontend/src/App.test.tsx` (A, +49, 2 tests), `src/test/setup.ts` (A, +1) |
| Frontend config / deps | `package.json` (A, +38), `package-lock.json` (A, +4666), `eslint.config.js` (A, +25), `vite.config.ts` (A, +26), `tsconfig.json` (A, +4), `tsconfig.app.json` (A, +23), `tsconfig.node.json` (A, +21), `.env.example` (A, +2), `.gitignore` (A, +5) |
| Documentation | `apps/navigator/README.md` (A, +79) |
| CI | `.github/workflows/ci.yml` (M, +18): new `navigator-frontend` job; `python` job untouched |

Not touched: `services/supply_api/**` (SUP), `pipelines/**`, `data/**` (read-only consumer), notebooks.
Shared-process interaction with SUP: both systems expose a top-level package `app`; navigator tests load it under the
alias `navigator_app` (`tests/conftest.py`) so root `pytest` runs both suites without collision (see K05).

## 4. Risk assessment (GAMP 5 / ICH Q9)

Method: GAMP 5 risk class = Severity × Probability (1 = highest, 3 = lowest); priority = class × Detectability
(High / Medium / Low).

| Risk ID | Hazard | Severity (H/M/L) | Probability (H/M/L) | Detectability (H/M/L) | Risk class | Mitigation / control |
|---|---|---|---|---|---|---|
| CCR-NAV-001-K01 | API serves data from the wrong or a stale directory (e.g. CWD-relative path), so reps see non-curated data | M | L | H | 3 → Low | Repo-relative default, explicit `NAVIGATOR_DATA_DIR` override, fail-closed `FileNotFoundError` (`app/data.py`); 5 tests in `test_data.py`; `/health` exposes `data_dir` and row counts |
| CCR-NAV-001-K02 | Rep→territory/region join error misattributes reps to regions | M | L | H | 3 → Low | Left join on `territory_id` (`list_reps`); `test_list_reps` asserts 30 reps, sort order, `R001`→`T001`/`South`, every rep has a region |
| CCR-NAV-001-K03 | Unauthenticated API: no access control on endpoints; CORS `allow_credentials=True` with configurable origins could widen exposure of HCP-related data | M | M | M | 2 → Medium | v0.1 exposes only reps/territories/health (no HCP, visit or follow-up endpoints); CORS defaults to localhost dev origins (`test_cors_allows_vite_dev_server`); no deployment in this change. GAP — access control and CORS hardening required before any non-dev deployment (Part 11 §11.10(d)); `/health` also discloses the absolute `data_dir` path |
| CCR-NAV-001-K04 | Upstream UC1 table change (missing table, row count or schema drift) breaks or silently changes API output | M | L | H | 3 → Low | `load_tables` fails on any missing table; tests pin row counts (`hcps` 1600, `reps` 30, `territories` 20) and response shape; pydantic models reject schema drift |
| CCR-NAV-001-K05 | `app` package-name collision with SUP in the shared pytest process tests the wrong module | L | M | H | 3 → Low | Relative imports only; `tests/conftest.py` loads the package as `navigator_app` via `importlib`; CI `python` job runs both suites (91 passed) |
| CCR-NAV-001-K06 | Unpinned backend dependency ranges (`>=`) give non-reproducible builds / unvalidated upgrades | M | M | M | 2 → Medium | Frontend lock file committed and installed with `npm ci`. GAP — pin backend requirements (lock/constraints file) before first approved release |
| CCR-NAV-001-K07 | Data held in memory only; lost on restart | L | H | H | 2 → Low | Accepted for v0.1: no records are created; tables are re-read from Git-versioned `data/*.parquet` at start-up. Recovery covered by DRP-NAV-001 |
| CCR-NAV-001-K08 | Scaffold mistaken for the Territory Call Planner (PRD features assumed present) | L | M | H | 3 → Low | Page subtitle states "UC4 scaffold"; this CCR and URS-NAV-001 list every PRD feature as `Not implemented in this change` |
| CCR-NAV-001-K09 | Change-process deviation: PR #8 authored and merged by the same identity (`devin-ai-integration[bot]`) with 0 recorded reviews; ticket MBA-3680 raised after the merge; PR #8 body does not reference MBA-3680 | M | H | H | 1 → Medium | Retrospective CCR (this record) per SOP-IT-002 §5.1; independent Technical Reviewer, System Owner and QA approval of this CCR and the sibling documents; GAP — QA to decide whether a deviation record is required for SOP-IT-002 §5.7 (merge by approver other than author) |

## 5. Verification and testing evidence

| Evidence | Location | Result |
|---|---|---|
| CI on PR head `53cf99e` — job `python` "Python lint + tests (data, pipelines, services)" | [run 41017579617 / job 123937293149](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41017579617/job/123937293149) | Success (2026-10-30 07:03 UTC) |
| CI on PR head `53cf99e` — job `navigator-frontend` "Navigator frontend (lint, test, build)" | [run 41017579617 / job 123937292874](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41017579617/job/123937292874) | Success (2026-10-30 07:02 UTC) |
| CI on merge commit `20e748e` (push to `main`) — job `python` | [run 41018019513 / job 123938658314](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41018019513/job/123938658314) | Success — ruff `All checks passed!`; pytest `91 passed` (repo-wide, incl. 9 navigator backend tests) |
| CI on merge commit `20e748e` — job `navigator-frontend` | [run 41018019513 / job 123938658722](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41018019513/job/123938658722) | Success — ESLint clean; vitest `1 passed` file, `2 passed` tests; `vite build` ✓ |
| Navigator backend tests (9) | `apps/navigator/backend/tests/test_data.py` (5), `tests/test_endpoints.py` (4) | Pass in CI; author re-ran `pytest apps/navigator/backend` on current `main` (`apps/navigator` and `ci.yml` identical to `20e748e`) → 9 passed |
| Navigator frontend tests (2) | `apps/navigator/frontend/src/App.test.tsx` | Pass in CI |
| Code review | PR #8 reviews | **None recorded** (0 reviews) — see K09 |

## 6. Implementation and back-out plan

**Implementation (done).** PR #8 merged to `main` as `20e748e` on 2026-10-30 07:06 UTC; post-merge CI green. No
deployment, configuration, infrastructure or data migration was performed. Run instructions:
`apps/navigator/README.md`.

**Back-out.** Open a PR that reverts the merge commit (`git revert -m 1 20e748e39c98d163c6d1f6fc2398254b3916d3f4`),
let CI pass and merge with System Owner approval. The change is purely additive (new `apps/navigator/**` tree plus
the new `navigator-frontend` CI job; `python` job, `services/**`, `pipelines/**` and `data/**` unchanged), so the
revert restores the pre-change state `7988df6` for code and CI with no data migration. Docs merged after the change
that describe the Navigator (e.g. `docs/DEMO_FLOW_UC4.md`) would need a follow-up docs update. Back-out trigger:
Technical Reviewer or QA rejects the change, or a Critical finding against K01–K09.

## 7. Controlled documents created or updated by this change (DOC-ID, version, PR)

Per SOP-IT-002 §6 "New validated system": create all four. Each is drafted by a separate Devin session with the org
playbook "GxP controlled document from change" as its own docs-only PR into `main` under
`docs/gxp/controlled/navigator/`.

| DOC-ID | Type | Version | PR |
|---|---|---|---|
| URS-NAV-001 | User Requirements Specification | 0.1 DRAFT (created) | Own docs-only PR (drafted in parallel; PR number recorded by QA at review) |
| FS-NAV-001 | Functional / Design Specification | 0.1 DRAFT (created) | Own docs-only PR (drafted in parallel; PR number recorded by QA at review) |
| DRP-NAV-001 | Disaster Recovery Plan | 0.1 DRAFT (created) | Own docs-only PR (drafted in parallel; PR number recorded by QA at review) |
| CCR-NAV-001 | Change Control Record | 0.1 DRAFT (this record) | This PR |

Also affected (baseline, not edited here): `docs/gxp/ESTATE_MAP.md` §4 NAV row (❌ → document IDs once approved) and
§2 NAV CI job name (map says `frontend`; actual job id is `navigator-frontend`).

## 8. Post-implementation review and closure criteria

QA closes CCR-NAV-001 when all of the following hold:

1. CI green on `main` at or after `20e748e` (met at `20e748e`, §5).
2. URS-NAV-001, FS-NAV-001, DRP-NAV-001 and CCR-NAV-001 approved by Technical Reviewer, System Owner and QA and
   merged (SOP-QA-001 §6); their PR numbers and versions recorded in §7.
3. K09 deviation dispositioned by QA (deviation record raised or justified as not required).
4. GAPs K03 (access control / CORS) and K06 (dependency pinning) accepted for v0.1 or tracked as tickets before any
   non-dev deployment.
5. PRD features and NFRs listed `Not implemented in this change` (§9) are tracked under a separate change
   (Territory Call Planner, MBA-3650), which requires its own CCR and URS/FS updates.
6. No incidents reported against Navigator 0.1.0.

## 9. Traceability matrix

Requirement IDs `CCR-NAV-001-Rnn` are local to this record; URS-NAV-001 (drafted in parallel) owns the authoritative
user-requirement IDs and the Technical Reviewer reconciles the mapping at review. Design refs point to FS-NAV-001
(parallel draft) and the as-built `apps/navigator/README.md`. All code and test paths verified at `20e748e`.

| Req ID | Requirement (short) | Source (ticket / PRD §) | Design ref | Code path(s) | Test(s) | Change ref (ticket / PR) | Status |
|---|---|---|---|---|---|---|---|
| CCR-NAV-001-R01 | `GET /health` returns `status="ok"`, version `0.1.0`, `data_dir` and row counts for all six tables | MBA-3680; PR #8 description | FS-NAV-001 (backend API); README "Run the backend" | `apps/navigator/backend/app/main.py` (`health`), `app/data.py` (`DataStore.row_counts`), `app/models.py` (`Health`) | `apps/navigator/backend/tests/test_endpoints.py::test_health_reports_row_counts` | MBA-3680 / PR #8 | Verified (CI) |
| CCR-NAV-001-R02 | `GET /reps` returns 30 reps sorted by `rep_id`, fields `rep_id, rep_name, territory_id, region, hire_date`, region joined from territories | MBA-3680; PR #8 description; PRD "Users" (rep selection) | FS-NAV-001 (backend API); README endpoint table | `apps/navigator/backend/app/main.py` (`list_reps`), `app/models.py` (`Rep`) | `apps/navigator/backend/tests/test_endpoints.py::test_list_reps` | MBA-3680 / PR #8 | Verified (CI) |
| CCR-NAV-001-R03 | `GET /territories` returns 20 territories sorted by `territory_id` across 5 regions | MBA-3680; PR #8 description | FS-NAV-001 (backend API); README endpoint table | `apps/navigator/backend/app/main.py` (`list_territories`), `app/models.py` (`Territory`) | `apps/navigator/backend/tests/test_endpoints.py::test_list_territories` | MBA-3680 / PR #8 | Verified (CI) |
| CCR-NAV-001-R04 | Load the six curated UC1 tables from `NAVIGATOR_DATA_DIR` or `<repo root>/data`; fail closed if the directory or a table is missing | PRD "Data"; PR #8 description | FS-NAV-001 (data access); README "Data" | `apps/navigator/backend/app/data.py` (`resolve_data_dir`, `load_tables`), `app/main.py` (`lifespan`, `get_store`) | `apps/navigator/backend/tests/test_data.py::test_default_data_dir_is_repo_root_data`, `::test_env_override`, `::test_relative_override_resolves_against_repo_root`, `::test_load_tables_missing_dir`, `::test_load_tables_reads_all_tables` | MBA-3680 / PR #8 | Verified (CI). GAP — no test for a single missing table inside an existing directory; add in next change |
| CCR-NAV-001-R05 | CORS allows only the Vite dev origins by default; override via `NAVIGATOR_CORS_ORIGINS` | PR #8 description; README | FS-NAV-001 (configuration); README "Run the backend" | `apps/navigator/backend/app/main.py` (`cors_origins`, `CORSMiddleware`) | `apps/navigator/backend/tests/test_endpoints.py::test_cors_allows_vite_dev_server` | MBA-3680 / PR #8 | Verified (CI) for default. GAP — env override and disallowed-origin rejection untested (see K03) |
| CCR-NAV-001-R06 | Frontend shows "Field Force Navigator", API status/row counts and a reps table; shows "API unreachable" on API error | PR #8 description | FS-NAV-001 (frontend); README "Run the frontend" | `apps/navigator/frontend/src/App.tsx`, `src/api.ts` | `apps/navigator/frontend/src/App.test.tsx::renders the title and lists reps from the API`, `::shows an error when the API is unreachable` | MBA-3680 / PR #8 | Verified (CI) |
| CCR-NAV-001-R07 | CI runs lint and tests on every PR (backend ruff + pytest; frontend lint, vitest, build) | PRD "Non-functional" (CI) | FS-NAV-001 (build/CI); README "CI" | `.github/workflows/ci.yml` (jobs `python`, `navigator-frontend`) | CI runs 41017579617 (PR) and 41018019513 (`main`), both jobs success | MBA-3680 / PR #8 | Verified (CI) — lint + tests + frontend build only; container build is R16 |
| CCR-NAV-001-R08 | Territory HCP list for the selected rep, filters (specialty, segment A/B/C, days since last visit) and name search (AC1) | PRD "In scope" 1, AC1 | FS-NAV-001 (not yet specified) | None at `20e748e` (no HCP endpoint or UI) | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement and verify under MBA-3650; new CCR + URS/FS update |
| CCR-NAV-001-R09 | Visit priority score 0–100 with plain-language reason; configurable weights A=40/B=25/C=10, +1/day max 40, +20 open follow-up, capped at 100 (AC2) | PRD "In scope" 2, AC2 | FS-NAV-001 (not yet specified) | None at `20e748e` (no scoring module) | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement and verify under MBA-3650; new CCR + URS/FS update |
| CCR-NAV-001-R10 | HCP visited in the last 7 days scores 0 (AC3) | PRD "In scope" 2, AC3 | FS-NAV-001 (not yet specified) | None at `20e748e` | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement and verify under MBA-3650; new CCR + URS/FS update |
| CCR-NAV-001-R11 | Weekly plan builder Mon–Fri; a 7th visit on a day is blocked with a message (AC4) | PRD "In scope" 3, AC4 | FS-NAV-001 (not yet specified) | None at `20e748e` (no plan endpoints or UI) | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement and verify under MBA-3650; new CCR + URS/FS update |
| CCR-NAV-001-R12 | Plan builder warns about duplicate HCPs in the plan | PRD "In scope" 3 | FS-NAV-001 (not yet specified) | None at `20e748e` | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement under MBA-3650 and add an acceptance criterion (PRD has none) |
| CCR-NAV-001-R13 | Warning names any Segment A HCP > 30 days overdue left off the plan (AC5) | PRD "In scope" 3, AC5 | FS-NAV-001 (not yet specified) | None at `20e748e` | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement and verify under MBA-3650; new CCR + URS/FS update |
| CCR-NAV-001-R14 | Plan exports as CSV with day, HCP, specialty, score and reason (AC6) | PRD "In scope" 3, AC6 | FS-NAV-001 (not yet specified) | None at `20e748e` | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — implement and verify under MBA-3650; new CCR + URS/FS update |
| CCR-NAV-001-R15 | Scoring logic has ≥ 90 % unit-test coverage | PRD "Non-functional" | FS-NAV-001 (not yet specified) | None at `20e748e` (depends on R09) | None (no coverage gate in CI) | MBA-3680 / PR #8 | Not implemented in this change. GAP — add coverage gate with the scoring module under MBA-3650 |
| CCR-NAV-001-R16 | CI runs a container build on every PR | PRD "Non-functional" | FS-NAV-001 (not yet specified) | None at `20e748e` (no Dockerfile, no container job in `.github/workflows/ci.yml`) | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — add Dockerfile + container CI job under MBA-3650 |
| CCR-NAV-001-R17 | HCP list loads in < 1 s for 300 HCPs | PRD "Non-functional" | FS-NAV-001 (not yet specified) | None at `20e748e` (depends on R08) | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — add performance test with R08 under MBA-3650 |
| CCR-NAV-001-R18 | Basic keyboard accessibility | PRD "Non-functional" | FS-NAV-001 (not yet specified) | Placeholder page only (`apps/navigator/frontend/src/App.tsx`, no interactive controls) | None | MBA-3680 / PR #8 | Not implemented in this change. GAP — add keyboard-accessibility checks with the interactive UI under MBA-3650 |

## 10. Impact on validated state

- Validated state before change: none for NAV — Field Force Navigator was not in the validated estate
  (`ESTATE_MAP.md` §4: URS/FS/DRP/CCR missing). Repository state before the change: `7988df6`.
- Components affected: new `apps/navigator/backend/**` (FastAPI API), new `apps/navigator/frontend/**` (React/Vite
  placeholder), `.github/workflows/ci.yml` (new `navigator-frontend` job). SUP (`services/supply_api`) unchanged; it
  shares the root pytest process (K05). Upstream UC1 data (`data/*.parquet`) read only.
- GxP impact assessment: **Indirect.** Navigator supports field-force planning around compliance-relevant HCP
  interaction records; it does not affect product quality, patient safety or batch release. v0.1 is read-only and
  exposes only reps, territories and health metadata.
- Data integrity (ALCOA+) impact: no records are created, modified or deleted; data is read from Git-versioned
  parquet (Original, Enduring, Available via Git history). Attributable: no user identity in v0.1 (no auth) —
  acceptable while read-only; required before any write feature (plans, R11–R14).
- Part 11 / Annex 11 controls affected: audit trail N/A (no writes); in-app e-signatures N/A (approvals are Git PR
  reviews); access control **none** in v0.1 (GAP — K03, required before non-dev deployment); backups/recovery via
  Git-versioned code and data, detailed in DRP-NAV-001.
- Revalidation required: **Full (initial validation)** — new system. Validated state is established at `20e748e` once
  URS-NAV-001, FS-NAV-001, DRP-NAV-001 and CCR-NAV-001 are approved. Later PRD features (R08–R18) need a new CCR with
  URS/FS updates and at least regression of R01–R07.
- Other controlled documents to update: URS-NAV-001, FS-NAV-001, DRP-NAV-001 (create, in parallel);
  `docs/gxp/ESTATE_MAP.md` §2/§4 NAV rows after approval.

## SOP-IT-002 §8 change control checklist

- [ ] C1 Ticket exists and links the PR(s); PR links the ticket — MBA-3680 links PR #8; PR #8 does not link MBA-3680 (ticket raised after merge). Partial; linked via this CCR and a Jira comment (K09)
- [x] C2 Change type and GxP impact classified with rationale — Normal / new validated system; GAMP 5 cat. 5; Indirect (§1, §10)
- [x] C3 Risk assessment recorded with mitigations — K01–K09 (§4)
- [x] C4 CI evidence recorded — runs 41017579617 / 41018019513, jobs `python` (91 passed) and `navigator-frontend` (2 passed, build ✓) (§5)
- [x] C5 Affected controlled documents listed with DOC-ID + version, each with its own PR — URS/FS/DRP/CCR-NAV-001 v0.1 DRAFT (§7); sibling PR numbers recorded at review
- [ ] C6 Author ≠ approver; merge commit recorded — merge commit `20e748e` recorded; PR #8 authored and merged by the same identity with no review (deviation K09)
- [x] C7 Back-out plan stated — revert `20e748e` via PR (§6)

## 11. Revision history

| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
| 0.1 DRAFT | 2026-10-30 | Devin (AI-drafted, playbook GxP controlled document from change) | MBA-3680 / PR #8 (merge `20e748e`) | First draft for Technical Reviewer, System Owner and QA review |
