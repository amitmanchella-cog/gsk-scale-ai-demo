# UC4 — Field Force Navigator: Phase 4 Test Report

Jira: [MBA-3650](https://cog-gtm.atlassian.net/browse/MBA-3650) · PR: [#14](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/14) · Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

## 1. Scope and method

Every acceptance criterion AC1–AC6 from the PRD was exercised **through the UI** of the running app (FastAPI backend on :8000 + Vite frontend, real `data/*.parquet`, default configuration, as-of date 2025-09-29) in **one continuous browser recording** (2 min 23 s, edited). Supplementary checks used the public API (`/api/scoring/explain`) and a read-only DOM comparison against the parquet data. No repository files were modified during verification.

- **Recording (AC1–AC6 in order):** [navigator-ac1-ac6-edited.mp4](https://devin-gtm.devinenterprise.com/attachments/92194806-44ea-4138-9062-f7c5e97e6672/navigator-ac1-ac6-edited.mp4)
- **Downloaded CSV (AC6):** [plan_R001_2025-09-29.csv](https://devin-gtm.devinenterprise.com/attachments/e08dddfc-48f9-4d21-a6a2-cbf48286e6a8/plan_R001_2025-09-29.csv)
- Automated gates on the same commit (CI, PR #14): Python lint + tests (84 backend tests, `navigator_app.scoring` coverage 100 % ≥ 90 % gate), frontend lint + 23 Vitest tests + build, container build + smoke (`/health`, `/api/reps`, `/api/reps/R001/hcps`, `/`) — all green.

## 2. Results

| AC | Given / When / Then (summary) | Observed | Result | Recording | Evidence |
|---|---|---|---|---|---|
| AC1 | Rep selected → only the rep's territory HCPs; filters/search narrow the list | R001 (Dev Okafor) → **64 HCPs in T001**; R002 (Hugo Rossi) → **82 in T002**. Oncology → 8; + Segment A → 2; + ≥ 50 days → 1 (H00915 Dr Hugo Walsh, 52 d); search `hUgO` keeps 1, `Isla` → 0 (AND semantics, case-insensitive). DOM check: all 64 rendered IDs = T001 parquet IDs. | **Pass** | 00:00–00:34 | [screenshot](https://devin-gtm.devinenterprise.com/attachments/148becd6-5685-469a-bd1e-e60675d63437/ss_343128ad.png) |
| AC2 | Segment A, ≥ 40 days since visit, 1 open follow-up → score 100 with readable reason | H00733 Dr Isla Xu: Segment A, 51 days (last 2025-08-09), 1 open follow-up, **score 100**, reason `Segment A (+40), 51 days since last visit (+40, capped), 1 open follow-up (+20)`. Literal PRD example via `/api/scoring/explain?segment=A&days_since_last_visit=45&open_follow_ups=1` → 100, `… 45 days since last visit (+40, capped) …`. | **Pass** | 00:35–00:48 | [screenshot](https://devin-gtm.devinenterprise.com/attachments/90134170-902b-453c-bc37-b60b0b7faa99/ss_3169dbee.png) |
| AC3 | Visited 3 days ago → score 0 with reason | H01331 Dr Finn Young: 3 days (last 2025-09-26), **score 0**, reason `Visited 3 days ago (within 7 days)`. | **Pass** | 00:50–00:58 | [screenshot](https://devin-gtm.devinenterprise.com/attachments/47df7062-2a62-4924-a764-dbe3369c5aa1/ss_17d93fb3.png) |
| AC4 | Day has 6 visits → 7th add blocked with a message | 6 distinct Monday visits added; with the HCP table scrolled, 7th add blocked: alert `Monday already has 6 visits (max 6)` scrolled into view and focused (`role="alert"`). Monday stays **6/6**, total 6, same six names. | **Pass** | 01:00–01:21 | [screenshot](https://devin-gtm.devinenterprise.com/attachments/74fec23e-015b-402d-b4ca-e498e710372f/ss_f2356395.png) |
| AC5 | Segment A HCP > 30 days overdue and unplanned → plan warns | Warning `Dr Isla Xu (Segment A) is 51 days overdue and not planned` shown; adding her to Tuesday (Tue 1/6, total 7) removed that warning, the other 8 overdue warnings remained. | **Pass** | 01:22–01:32 | [screenshot](https://devin-gtm.devinenterprise.com/attachments/5668c38a-b71a-49b7-b7c5-a9fb8bb30812/ss_e903f142.png) |
| AC6 | Completed plan → CSV downloads with day, HCP, specialty, score, reason; Mon→Fri then score desc | Downloaded **`plan_R001_2025-09-29.csv`** (1,183 bytes, `text/csv`). Header `day,hcp_id,hcp_name,specialty,segment,score,reason`; 11 visit rows (Mon 6 / Tue 1 / Wed 1 / Thu 1 / Fri 2); Mon→Fri, score desc within day (Mon 100,100,100,85,85,0; Fri Isla 100 before Finn 0) despite out-of-order insertion; comma-bearing reasons RFC 4180-quoted, 7 fields per row via `csv.reader`, CRLF line endings. Empty plan → Export CSV `aria-disabled`, no href, no download. | **Pass** | 01:33–02:09, 02:21 | [screenshot](https://devin-gtm.devinenterprise.com/attachments/0bb1ae9d-8aae-46c3-b7c9-3f364aab59ed/ss_2694446e.png) |

Additional flows verified in the same recording:

| Flow | Observed | Result | Recording |
|---|---|---|---|
| Duplicate add (S3.3) | Allowed with warnings `Dr Finn Young is planned 4 times (Mon, Fri, Thu, Wed)`, `Dr Isla Xu is planned twice (Tue, Fri)` | Pass | 02:12 |
| Remove visit (S3.4) | Removing Friday Finn: Fri 2/6 → 1/6, total 11 → 10, warning becomes `planned 3 times (Mon, Thu, Wed)` | Pass | 02:15 |
| Clear plan (S3.4) | All days 0/6, total 0, 12 overdue warnings return, export disabled | Pass | 02:20 |

## 3. Traceability to automated tests

| AC | Backend (pytest) | Frontend (Vitest) |
|---|---|---|
| AC1 | `test_hcps.py::test_ac1_only_territory_hcps`, `::test_ac1_filters_and_search`, `::test_unknown_rep_404`, `::test_sort_order` | `HcpList › filters and search narrow the list` |
| AC2 | `test_scoring.py::test_ac2_segment_a_45_days_open_follow_up` (+ boundary/config tests, 100 % coverage) | — |
| AC3 | `test_scoring.py::test_ac3_recent_visit_scores_zero` | — |
| AC4 | `test_plan.py::test_ac4_seventh_visit_blocked` | `PlanBuilder › blocks the 7th visit with a message` |
| AC5 | `test_plan.py::test_ac5_overdue_segment_a_warning` | `PlanBuilder › warns about unplanned overdue Segment A` |
| AC6 | `test_export.py::test_ac6_csv_columns_and_rows`, `::test_reason_commas_quoted`, `::test_empty_plan_header_only` | `PlanBuilder › export downloads a CSV` |
| NFR | `test_perf.py::test_300_hcps_under_1s` (p95 ≈ 0.02 s), `test_server.py` (container entrypoint) | `a11y.test.tsx` (4 tests) |

## 4. Not covered by this run

- Container / deployed-environment UI run (container is smoke-tested in CI, not driven through the browser).
- Non-default configuration (`NAVIGATOR_SCORING_RULES`, `NAVIGATOR_MAX_VISITS_PER_DAY`, `NAVIGATOR_OVERDUE_DAYS`) — covered by unit tests only.
- Cross-browser / full keyboard matrix and screen-reader announcements (keyboard-only walkthrough was done on the S5 container PR #13).
- HTTP 409 status code was asserted by `test_ac4_seventh_visit_blocked`, not captured separately in the browser.

## 5. Verdict

**All six acceptance criteria pass** on commit `3c26c7a` of `devin/MBA-3650` (PR #14, CI green). Ready for the phase-4 gate.
