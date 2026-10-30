# URS-NAV-001 — Field Force Navigator: User Requirements Specification

> **AI-drafted controlled document, pending review.** Synthetic, written for the GSK Scale AI demo; no real GSK
> systems, people or data. Describes Navigator **as built at merge commit `20e748e`** (PR #8) against the
> requirements in `docs/uc4/PRD.md`. PRD features not delivered by this change are listed with status
> `Not implemented in this change` and a `GAP —` note.

| Field | Value |
|---|---|
| Document ID | URS-NAV-001 |
| Document type | URS |
| Version | 0.1 DRAFT |
| Status | Draft |
| System | Field Force Navigator (`apps/navigator`) |
| GAMP 5 category | 5 (custom application) |
| GxP impact | Indirect — reads HCP interaction records (visits, follow-ups) used for compliance-relevant call planning; no direct patient, product-quality or batch-release decision (see §8) |
| Change reference | Jira [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680), PR [#8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8) "UC4: scaffold Field Force Navigator (FastAPI + React/Vite)", merge commit `20e748e39c98d163c6d1f6fc2398254b3916d3f4` |
| Author | Devin (AI-drafted, playbook GxP controlled document from change) — session https://devin-gtm.devinenterprise.com/sessions/9b6d5495414a46569c148547fe272f38 |
| Effective date | <set by QA on approval> |
| Governing SOPs | SOP-QA-001, SOP-IT-002 |

## Approvals

| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | Devin (AI-drafted, playbook GxP controlled document from change) | Authored and technically accurate | |
| System Owner | | Content fit for intended use | |
| Technical Reviewer | | Matches the code and tests at the referenced commit | |
| Quality Assurance | | Complies with SOP-QA-001 and the template | |

> Electronic signatures follow 21 CFR Part 11 §11.50/§11.70 (name, date/time, meaning) in the system of record.
> In this demo the system of record is the Git PR: approval = PR review "Approve" by the named role.
> The AI author does not sign or approve this document (SOP-QA-001 §3).

## 1. Purpose and scope

Field Force Navigator lets field reps build a prioritised weekly call plan for healthcare professionals (HCPs) in
their territory, and lets district managers review those plans (`docs/uc4/PRD.md` §Problem, §Users, §Goal).

**Users:** field rep (plans own week); district manager (reviews reps' plans).

**In scope of this version (v0.1, PR #8 scaffold):** a FastAPI backend that loads the curated UC1 tables
(`data/*.parquet`) into memory and serves `GET /health`, `GET /reps` and `GET /territories`; a React/Vite
placeholder page that shows API status and the rep list; CI lint + test jobs.

**Specified but not implemented in this version:** the three PRD features — Territory HCP list, Visit priority
score, Weekly plan builder with CSV export — and the PRD non-functional requirements beyond lint/tests
(scoring coverage, container build, performance, accessibility). They are recorded as requirements R09–R22 so that
later changes can be traced against this URS.

**Out of scope** (PRD §Out of scope): integration with a real CRM (e.g. Veeva), real HCP data or PII, SSO, mobile
app, route optimisation, GenAI features.

## 2. Regulatory context and system classification

- **GAMP 5 Category 5** — bespoke application code (FastAPI backend + React frontend) written for this purpose
  (`docs/gxp/ESTATE_MAP.md` §2; MBA-3680 classification).
- **GxP impact: Indirect.** The system reads HCP interaction records (visits, follow-ups) and will drive call
  planning that is compliance-relevant (HCP engagement), but makes no patient-safety, product-quality or release
  decision. v0.1 is read-only and creates no records.
- **Applicable regulations:** 21 CFR Part 11 and EU GMP Annex 11 apply to electronic records once Navigator
  creates or persists them (weekly plans, exports). v0.1 holds data in process memory only and creates no records;
  controls are required before plan persistence is introduced (R23, R24). ICH E6 — N/A (no clinical trial data).
- **Data classification:** synthetic, deterministic (seed 42, `data/generate.py`); no real people, products or places.

## 3. Definitions and references

| Term | Meaning |
|---|---|
| HCP | Healthcare professional (synthetic record in `data/hcps.parquet`) |
| Segment | HCP priority tier A/B/C (`hcps.segment`) |
| Curated tables | UC1 outputs read by Navigator: `hcps`, `visits`, `follow_ups`, `reps`, `territories`, `weekly_sales` |
| Scaffold | v0.1 delivered by PR #8: data loading, `/health`, `/reps`, `/territories`, placeholder UI |

References:
- Change ticket [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680); code change
  [PR #8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8), merge commit `20e748e`;
  CI run [41018019513](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41018019513) (success).
- Requirements source: [`docs/uc4/PRD.md`](../../../uc4/PRD.md) (Territory Call Planner PRD); `apps/navigator/README.md`.
- SOP-QA-001 (Controlled Document Authoring & Review), SOP-IT-002 (Change Control), `docs/gxp/ESTATE_MAP.md`.
- Sibling controlled documents for this change (drafted in parallel, separate PRs): FS-NAV-001 (Functional /
  Design Specification), DRP-NAV-001 (Disaster Recovery Plan), CCR-NAV-001 (Change Control Record).

## 4. User requirements

Priority: M (mandatory) / D (desirable). Status of each requirement at `20e748e` is in §7.

| Req ID | Category | Requirement | Acceptance criterion | Priority | Source |
|---|---|---|---|---|---|
| URS-NAV-001-R01 | Availability & recovery | The service exposes a health check reporting version and data load status | `GET /health` returns 200 with `status` = `"ok"`, `version` = `0.1.0`, `data_dir`, and `row_counts` for all six curated tables, each > 0 | M | PR #8; README §Run the backend |
| URS-NAV-001-R02 | Data | The system loads the curated UC1 tables from a controlled location and fails closed if they are missing | All six tables load from `<repo root>/data` by default or from `NAVIGATOR_DATA_DIR` (absolute, or relative to repo root); a missing directory or table raises `FileNotFoundError` instead of serving partial data; `hcps` loads 1 600 rows | M | PRD §Data; PR #8 |
| URS-NAV-001-R03 | Functional | Users can list reps with their territory and region | `GET /reps` returns 30 reps sorted by `rep_id`, each with exactly `rep_id`, `rep_name`, `territory_id`, `region`, `hire_date`; `region` joined from territories and never empty; R001 → T001 / South | M | PRD §Users; PR #8 |
| URS-NAV-001-R04 | Functional | Users can list territories | `GET /territories` returns 20 territories sorted by `territory_id`; first = `{T001, South-01, South}`; regions = {Central, East, North, South, West} | M | PRD §Data; PR #8 |
| URS-NAV-001-R05 | Interface | The web UI shows API status and the rep list, and reports when the API is unreachable | Page shows heading "Field Force Navigator", "API ok", per-table row counts and a "Reps (n)" table; on a non-2xx API response it shows "API unreachable: …" | M | PR #8 |
| URS-NAV-001-R06 | Security & access | The API accepts browser calls only from configured origins | CORS pre-flight from `http://localhost:5173` is allowed by default; allowed origins are overridable with comma-separated `NAVIGATOR_CORS_ORIGINS` | M | PR #8; README |
| URS-NAV-001-R07 | Regulatory | Only synthetic data is used; no real HCP data or PII | Curated tables come from the seeded generator (`SEED = 42`), are deterministic across runs and referentially consistent | M | PRD §Out of scope, §Data |
| URS-NAV-001-R08 | Regulatory | Every PR is verified by CI lint and automated tests | CI jobs `python` (ruff + pytest incl. `apps`) and `navigator-frontend` (eslint, vitest, build) run on every PR and push to `main` and pass | M | PRD §Non-functional; SOP-IT-002 §5.5 |
| URS-NAV-001-R09 | Functional | A rep sees only the HCPs in their own territory | Given a rep is selected, when the HCP list opens, only HCPs whose `territory_id` equals the rep's territory appear (AC1) | M | PRD §In scope "Territory HCP list"; AC1 |
| URS-NAV-001-R10 | Functional | The rep can filter the HCP list by specialty, segment (A/B/C) and days since last visit, and search by name | Each filter and the name search narrow the list to exactly the matching HCPs (AC1) | M | PRD "Territory HCP list"; AC1 |
| URS-NAV-001-R11 | Functional | Each HCP gets a 0–100 visit priority score from the documented rules | Segment weight A=40, B=25, C=10; +1 per day since last visit, max 40; +20 for an open follow-up; total capped at 100. Segment A, 45 days, 1 open follow-up → 100 (AC2) | M | PRD "Visit priority score"; AC2 |
| URS-NAV-001-R12 | Functional | Each score has a plain-language reason | Reason text lists every contributing factor, e.g. "Segment A, 45 days since last visit, 1 open follow-up" (AC2) | M | PRD "Visit priority score"; AC2 |
| URS-NAV-001-R13 | Functional | HCPs visited in the last 7 days score 0 | HCP visited 3 days ago → score 0 (AC3) | M | PRD "Visit priority score"; AC3 |
| URS-NAV-001-R14 | Functional | Scoring rules are configurable | Changing a segment weight, day cap or follow-up bonus in configuration changes the computed score accordingly without code change | M | PRD "The rules are configurable" |
| URS-NAV-001-R15 | Functional | The rep builds a Mon–Fri weekly plan with at most 6 visits per day | Adding a 7th visit to a day is blocked with a message (AC4) | M | PRD "Weekly plan builder"; AC4 |
| URS-NAV-001-R16 | Functional | The plan warns about duplicate HCPs | Adding an HCP already in the plan shows a duplicate warning | M | PRD "Weekly plan builder" |
| URS-NAV-001-R17 | Functional | The plan warns about overdue Segment A HCPs left off the plan | A Segment A HCP > 30 days since last visit and not in the plan is named in a warning (AC5) | M | PRD "Weekly plan builder"; AC5 |
| URS-NAV-001-R18 | Interface | The plan exports as CSV | Export of a completed plan downloads a CSV with columns day, HCP, specialty, score, reason (AC6) | M | PRD "Weekly plan builder"; AC6 |
| URS-NAV-001-R19 | Performance | The HCP list loads quickly | HCP list for 300 HCPs loads in < 1 s | M | PRD §Non-functional |
| URS-NAV-001-R20 | Regulatory | Scoring logic is thoroughly unit tested | Unit-test line coverage of the scoring module ≥ 90 % | M | PRD §Non-functional |
| URS-NAV-001-R21 | Regulatory | CI builds the container on every PR | CI includes a container build job that passes on every PR | M | PRD §Non-functional |
| URS-NAV-001-R22 | Interface | Basic keyboard accessibility | HCP list, filters, plan builder and export are operable by keyboard only (focus order, visible focus, Enter/Space activation) | M | PRD §Non-functional |
| URS-NAV-001-R23 | Security & access | Plan actions are attributable to a named user | Every plan create/change/export records the acting rep's identity; district managers can see only their reps' plans | M (before plans are persisted) | PRD §Users; Annex 11 §12; SOP-QA-001 §2 (ALCOA+ Attributable) |
| URS-NAV-001-R24 | Audit trail / data integrity | Changes to persisted plans are audit-trailed | Each create/update/delete of a plan record stores who, when (UTC) and old/new values; the trail cannot be edited by users | M (before plans are persisted) | 21 CFR 11.10(e); Annex 11 §9 |
| URS-NAV-001-R25 | Performance | A rep can build a prioritised weekly plan in under 5 minutes | Timed user walkthrough from rep selection to CSV export completes in < 5 min | D | PRD §Goal |
| URS-NAV-001-R26 | Functional | District managers can review their reps' plans | A district manager can open and read (not edit) the weekly plan of each rep they manage | D | PRD §Users |

## 5. Data integrity (ALCOA+) requirements

- **Attributable:** N/A for v0.1 — no users, no authentication, no records created (SSO out of scope per PRD).
  **GAP —** R23 must be met before plans are persisted.
- **Legible:** API returns typed JSON via pydantic models (`Health`, `Rep`, `Territory`); UI renders tables. Met.
- **Contemporaneous:** N/A for v0.1 — no records are created. **GAP —** R24 (UTC timestamps) for plan records.
- **Original:** the curated UC1 parquet files in `data/` are the source of truth; Navigator holds a read-only
  in-memory copy loaded at startup (R02) and never writes back.
- **Accurate:** deterministic seeded data (R07) and automated tests asserting row counts and joins (R01–R04).
  Scoring accuracy (R11–R13) — **GAP**, not implemented.
- **Complete:** load fails closed if any of the six tables is missing (R02); `/health` exposes per-table row counts.
- **Consistent:** referential integrity of the curated tables is tested (`data/tests/test_generate.py::test_referential_integrity`); region join in `/reps` never empty (R03).
- **Enduring:** source data is version-controlled in Git; v0.1 keeps no state of its own. Plan persistence and its
  backup — **GAP —** to be covered by DRP-NAV-001 when introduced.
- **Available:** data available via `GET /reps`, `GET /territories`; availability monitored via `GET /health` (R01).

## 6. Constraints and assumptions

- Python 3.11 in CI (ruff `target-version` py310), FastAPI ≥ 0.110, pydantic v2, pandas ≥ 2.0 + pyarrow ≥ 14;
  Node 20, React 18, Vite 5, vitest (`apps/navigator/backend/requirements.txt`, `apps/navigator/frontend/package.json`).
- Single process; all tables held in memory; no database; no authentication (v0.1).
- Upstream dependency: curated tables produced by UC1 (`data/generate.py`, `pipelines/territory_kpis`); changes to
  `data/**` trigger NAV impact assessment (ESTATE_MAP §6).
- The backend package is named `app`; tests load it under alias `navigator_app` to avoid collision with
  `services/supply_api` in a single pytest process.
- Synthetic data only. Assumes the PRD (`docs/uc4/PRD.md`) is the approved requirements source for NAV.

## 7. Traceability matrix

Design references point to the sibling FS-NAV-001 by function/endpoint; FS function IDs are to be aligned when
FS-NAV-001 is approved. Code paths are relative to `apps/navigator/` unless stated. Frontend tests are vitest
`describe('App') › it(...)` names in `frontend/src/App.test.tsx`.

| Req ID | Requirement (short) | Source (ticket / PRD §) | Design ref | Code path(s) | Test(s) | Change ref (ticket / PR) | Status |
|---|---|---|---|---|---|---|---|
| R01 | Health check | PR #8; README | FS-NAV-001 — `GET /health` | `backend/app/main.py` (`health`), `backend/app/models.py` (`Health`), `backend/app/__init__.py` (`__version__`) | `backend/tests/test_endpoints.py::test_health_reports_row_counts` | MBA-3680 / PR #8 | Verified |
| R02 | Load curated tables, fail closed | PRD §Data; PR #8 | FS-NAV-001 — data loading (`load_tables`, `NAVIGATOR_DATA_DIR`) | `backend/app/data.py` (`resolve_data_dir`, `load_tables`, `DataStore`), `backend/app/main.py` (`lifespan`, `get_store`) | `backend/tests/test_data.py::test_default_data_dir_is_repo_root_data`, `::test_env_override`, `::test_relative_override_resolves_against_repo_root`, `::test_load_tables_missing_dir`, `::test_load_tables_reads_all_tables` | MBA-3680 / PR #8 | Verified (missing-single-table branch untested — GAP below) |
| R03 | List reps with region | PRD §Users; PR #8 | FS-NAV-001 — `GET /reps` | `backend/app/main.py` (`list_reps`), `backend/app/models.py` (`Rep`) | `backend/tests/test_endpoints.py::test_list_reps` | MBA-3680 / PR #8 | Verified |
| R04 | List territories | PRD §Data; PR #8 | FS-NAV-001 — `GET /territories` | `backend/app/main.py` (`list_territories`), `backend/app/models.py` (`Territory`) | `backend/tests/test_endpoints.py::test_list_territories` | MBA-3680 / PR #8 | Verified |
| R05 | UI status + rep list | PR #8 | FS-NAV-001 — frontend placeholder page | `frontend/src/App.tsx`, `frontend/src/api.ts` (`fetchHealth`, `fetchReps`), `frontend/vite.config.ts` (`/api` proxy) | `frontend/src/App.test.tsx` › "renders the title and lists reps from the API", › "shows an error when the API is unreachable" | MBA-3680 / PR #8 | Verified |
| R06 | CORS restricted to configured origins | PR #8; README | FS-NAV-001 — CORS configuration | `backend/app/main.py` (`DEFAULT_CORS_ORIGINS`, `cors_origins`, `CORSMiddleware`) | `backend/tests/test_endpoints.py::test_cors_allows_vite_dev_server` | MBA-3680 / PR #8 | Partially verified — GAP — add test for `NAVIGATOR_CORS_ORIGINS` override and a disallowed origin |
| R07 | Synthetic data only | PRD §Out of scope, §Data | FS-NAV-001 — data model (UC1 curated tables) | `data/generate.py` (`SEED = 42`), `data/*.parquet` (repo root) | `data/tests/test_generate.py::test_generator_is_deterministic`, `::test_referential_integrity`, `::test_table_exists_and_non_empty` | MBA-3680 / PR #8 (consumes existing UC1 data) | Verified |
| R08 | CI lint + tests on every PR | PRD §Non-functional; SOP-IT-002 §5.5 | FS-NAV-001 — build & CI; CCR-NAV-001 (CI evidence) | `.github/workflows/ci.yml` (jobs `python`, `navigator-frontend`), `pyproject.toml` (`testpaths` incl. `apps`) | CI run 41018019513 on `20e748e`: `Python lint + tests` success, `Navigator frontend (lint, test, build)` success; backend `9 passed`, frontend `2 passed` (PR #8) | MBA-3680 / PR #8 | Verified |
| R09 | Territory-scoped HCP list | PRD "Territory HCP list"; AC1 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` (no HCP endpoint or UI) | None | GAP — future change under MBA project | Not implemented in this change — GAP — implement HCP list endpoint + UI and AC1 tests |
| R10 | HCP filters + name search | PRD "Territory HCP list"; AC1 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement filters/search with AC1 tests |
| R11 | Priority score 0–100 rules | PRD "Visit priority score"; AC2 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` (no scoring module) | None | GAP — future change | Not implemented in this change — GAP — implement scoring with AC2 test |
| R12 | Plain-language reason | PRD "Visit priority score"; AC2 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement reason text with AC2 test |
| R13 | Visited ≤ 7 days → 0 | PRD "Visit priority score"; AC3 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement with AC3 test |
| R14 | Configurable scoring rules | PRD "Visit priority score" | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement rule configuration + tests |
| R15 | Mon–Fri plan, max 6/day | PRD "Weekly plan builder"; AC4 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` (no plan model or endpoint) | None | GAP — future change | Not implemented in this change — GAP — implement plan builder with AC4 test |
| R16 | Duplicate warning | PRD "Weekly plan builder" | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement + test |
| R17 | Overdue Segment A warning | PRD "Weekly plan builder"; AC5 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement with AC5 test |
| R18 | CSV export | PRD "Weekly plan builder"; AC6 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — implement export with AC6 test |
| R19 | HCP list < 1 s for 300 HCPs | PRD §Non-functional | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — add timed test once R09 exists |
| R20 | Scoring coverage ≥ 90 % | PRD §Non-functional | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None (no coverage gate in `ci.yml`) | GAP — future change | Not implemented in this change — GAP — add scoring module + coverage gate |
| R21 | Container build in CI | PRD §Non-functional | FS-NAV-001 — build & CI; DRP-NAV-001 (rebuild) | None at `20e748e` (no Dockerfile; `ci.yml` has no container job) | None | GAP — future change | Not implemented in this change — GAP — add Dockerfile + CI container job |
| R22 | Keyboard accessibility | PRD §Non-functional | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` (placeholder page only, no interactive controls) | None | GAP — future change | Not implemented in this change — GAP — add keyboard tests with R09–R18 UI |
| R23 | Attributable plan actions / access | PRD §Users; Annex 11 §12 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` (no authentication) | None | GAP — future change | Not implemented in this change — GAP — required before plans are persisted; SSO out of scope, define alternative |
| R24 | Audit trail for plan records | 21 CFR 11.10(e); Annex 11 §9 | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` (no persisted records) | None | GAP — future change | Not implemented in this change — GAP — required before plans are persisted |
| R25 | Plan in < 5 min | PRD §Goal | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — timed UAT once R09–R18 exist |
| R26 | Manager review of plans | PRD §Users | FS-NAV-001 — not specified at `20e748e` | None at `20e748e` | None | GAP — future change | Not implemented in this change — GAP — confirm scope with System Owner |

## 8. Impact on validated state

- Validated state before change: none — Navigator is a new system in the validated estate (ESTATE_MAP §4: NAV had
  no controlled documents). After approval: v0.1 at merge commit `20e748e`.
- Components affected: `apps/navigator/backend` (`app/main.py`, `app/data.py`, `app/models.py`), `apps/navigator/frontend`
  (`src/App.tsx`, `src/api.ts`, `vite.config.ts`), `.github/workflows/ci.yml` (new `navigator-frontend` job);
  reads (does not modify) `data/*.parquet`.
- GxP impact assessment: **Indirect** — HCP interaction data supports compliance-relevant call planning; v0.1 is
  read-only, creates no records and makes no decision.
- Data integrity (ALCOA+) impact: none for v0.1 — read-only in-memory copy of synthetic source data (§5). Attributable
  and audit-trail controls are open gaps (R23, R24) that must close before any plan data is persisted.
- Part 11 / Annex 11 controls affected: audit trail, e-signatures and access control N/A for v0.1 (no persisted
  records, no users); backups N/A for v0.1 (stateless, source in Git) — reassess with DRP-NAV-001 when persistence
  is added.
- Revalidation required: **Full initial validation of v0.1 scope** (R01–R08; CI evidence: 9 backend + 2 frontend
  automated tests, CI run 41018019513 green). R09–R26 are validated when implemented, each under its own change and
  CCR with a URS-NAV-001 update.
- Other controlled documents to update: FS-NAV-001 (create), DRP-NAV-001 (create), CCR-NAV-001 (create) per
  SOP-IT-002 §6 "New validated system".

## 9. Revision history

| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
| 0.1 DRAFT | 2026-10-30 | Devin (AI-drafted, playbook GxP controlled document from change) | MBA-3680 / PR #8 (merge commit `20e748e`) | First draft: v0.1 scaffold requirements R01–R08 verified at `20e748e`; PRD features and NFRs R09–R26 recorded as not implemented in this change with GAP notes |
