# DRP-NAV-001 — Field Force Navigator: Disaster Recovery Plan

> Controlled document (DRAFT). Synthetic, written for the GSK Scale AI demo; no real GSK systems, people or data.

| Field | Value |
|---|---|
| Document ID | DRP-NAV-001 |
| Document type | DRP |
| Version | 0.1 DRAFT |
| Status | Draft |
| System | Field Force Navigator (`apps/navigator`) |
| GAMP 5 category | 5 (custom application) |
| GxP impact | Indirect (HCP interaction records, compliance-relevant; justified in §11) |
| Change reference | [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680), PR [#8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8) + merge commit `20e748e39c98d163c6d1f6fc2398254b3916d3f4` |
| Author | Devin (AI-drafted, playbook GxP controlled document from change) — session https://devin-gtm.devinenterprise.com/sessions/0d79cc7b00ed4b6d8b27d96e6ee16bf3 |
| Effective date | _set by QA on approval_ |
| Governing SOPs | SOP-QA-001, SOP-IT-002 |

## Approvals

| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | Devin (AI-drafted, playbook GxP controlled document from change) | Authored and technically accurate | _not self-approved (SOP-QA-001 §3)_ |
| System Owner | | Content fit for intended use; recovery objectives accepted | |
| Technical Reviewer | | Matches the code and tests at the referenced commit; procedures executable at `20e748e` | |
| Quality Assurance | | Complies with SOP-QA-001 and the template | |

> Electronic signatures follow 21 CFR Part 11 §11.50/§11.70 (name, date/time, meaning) in the system of record.
> In this demo the system of record is the Git PR: approval = PR review "Approve" by the named role.

Related controlled documents for the same change (drafted in parallel, referenced by ID only): URS-NAV-001 (User
Requirements), FS-NAV-001 (Functional / Design Specification), CCR-NAV-001 (Change Control Record).

## 1. Purpose and scope

Defines how the Field Force Navigator v0.1 is recovered after a disruption so that it returns to its validated state
at commit `20e748e` (PR #8, MBA-3680). Applies EU GMP Annex 11 §7 (data storage, backups) and §16 (business
continuity).

**In scope (as built at `20e748e`; `apps/navigator` is unchanged on `main` since):**

| Component | Path | What it does |
|---|---|---|
| Backend API | `apps/navigator/backend/app/main.py` | FastAPI app, version `0.1.0` (`app/__init__.py`); read-only endpoints `GET /health`, `GET /territories`, `GET /reps`; CORS via `NAVIGATOR_CORS_ORIGINS` |
| Data loader | `apps/navigator/backend/app/data.py` | `load_tables()` reads 6 Parquet tables into memory at start-up from `NAVIGATOR_DATA_DIR` or `<repo root>/data`; raises `FileNotFoundError` if the directory or a table is missing |
| Response models | `apps/navigator/backend/app/models.py` | `Health`, `Territory`, `Rep` |
| Frontend | `apps/navigator/frontend/src/App.tsx`, `src/api.ts` | React 18 / Vite 5 placeholder page: calls `/api/health` and `/api/reps`; shows "API unreachable: …" on failure |
| Curated data (upstream, UC1) | `data/*.parquet`, `data/generate.py` | `hcps` 1600, `visits` 4611, `follow_ups` 1393, `reps` 30, `territories` 20, `weekly_sales` 2080 rows; seed-42 deterministic generator |
| CI | `.github/workflows/ci.yml` | jobs `python` (ruff + pytest) and `navigator-frontend` (npm ci, lint, vitest, build) |

**Environments covered:** developer / demo environment run from source (the only environment defined at `20e748e`).
**Out of scope:** hosted non-prod/prod environments, container images and deployment pipelines — none exist at
`20e748e` (`git ls-tree` shows no Dockerfile or deploy workflow). See GAP-01.

## 2. Criticality and recovery objectives

| Item | Value | Rationale |
|---|---|---|
| Business criticality | Low (v0.1) — re-assess to Medium when the weekly plan builder (PRD feature 3) is released | v0.1 is a read-only scaffold listing reps/territories; no rep workflow depends on it yet. Reps keep planning from their existing spreadsheets (PRD "Problem") |
| RTO (recovery time objective) | 4 h | Full rebuild from Git (pip install + npm ci + build + verification) took < 5 min in the 2026-10-30 drill (§9.3); 4 h covers Git-host or registry outages (S04, S05) |
| RPO (recovery point objective) | Last merge commit on `main` (zero loss of records) | The application writes no data: all endpoints are `GET`, state is an in-memory copy of `data/*.parquet`, which is version-controlled and regenerable bit-for-bit (`data/generate.py`, seed 42) |
| Maximum tolerable downtime | 5 working days | Indirect GxP impact; no records are created; manual planning fallback exists. Re-assess with the plan builder (GAP-03) |

## 3. System inventory for recovery

| Item | Value |
|---|---|
| Source repo + commit | `amitmanchella-cog/gsk-scale-ai-demo` @ `20e748e39c98d163c6d1f6fc2398254b3916d3f4` (validated baseline for NAV v0.1) |
| Backend runtime | Python 3.11 in CI (`actions/setup-python`), ≥ 3.10 supported (`pyproject.toml` `target-version = "py310"`); `apps/navigator/backend/requirements.txt`: `fastapi>=0.110`, `uvicorn>=0.29`, `pandas>=2.0`, `pyarrow>=14`, `pydantic>=2.6`, `httpx>=0.27`, `pytest>=8` (lower bounds only — GAP-04) |
| Frontend runtime | Node ≥ 20 (`package.json` `engines`; CI uses Node 20); dependencies pinned by committed `apps/navigator/frontend/package-lock.json` (`npm ci`) |
| Build artefacts | None published. Frontend `dist/` produced by `npm run build` (`tsc -b && vite build`); backend runs from source. No container image at `20e748e` (GAP-01) |
| Configuration | Env vars only: `NAVIGATOR_DATA_DIR` (absolute, or relative to repo root; default `<repo root>/data`), `NAVIGATOR_CORS_ORIGINS` (comma-separated; default `http://localhost:5173,http://127.0.0.1:5173`), `VITE_API_BASE` (Vite dev proxy target; default `http://localhost:8000`, see `frontend/.env.example`) |
| Data stores | `data/{hcps,visits,follow_ups,reps,territories,weekly_sales}.parquet` (≈ 148 KB total), committed in Git; loaded read-only into memory at start-up. No database |
| Secrets (names only) | None. The application uses no credentials, tokens or keys |
| Upstream dependency | UC1 curated tables (`pipelines/territory_kpis`, `data/generate.py`) |

## 4. Backup and restore strategy

| What | Where (backup) | Frequency | Retention | Restore method | Restore test cadence |
|---|---|---|---|---|---|
| Application source + CI config | Git (GitHub, `main` + merge commits, PR history) | Every merge (continuous) | Life of system + 5 years (SOP-IT-002 §7) | `git checkout <commit>` | Every PR (CI rebuilds from a clean checkout) + annual drill (§9) |
| Curated data `data/*.parquet` | Git (same repo) **and** regenerable from `data/generate.py` (seed 42) | Every merge touching `data/**` | As above | `git checkout <commit> -- data/` or `python data/generate.py --out <dir>` | CI `data/tests/test_generate.py::test_generator_is_deterministic` on every PR + annual drill |
| Frontend dependencies | `package-lock.json` in Git; npm registry | Every merge | As above | `npm ci` | Every PR (`navigator-frontend` job) |
| Backend dependencies | `requirements.txt` in Git; PyPI | Every merge | As above | `pip install -r …` | Every PR (`python` job) — versions float (GAP-04) |
| Off-platform copy of the repository | **Not configured in this demo** (GAP-02) | — | — | `git clone --mirror` / `git bundle` restore (§6 S04) | Annual drill once configured |
| Application records (audit trail, plans) | N/A — v0.1 creates no records | — | — | — | Re-assess with PRD feature 3 (GAP-03) |

## 5. Disaster scenarios

| Scenario ID | Scenario | Detection | Recovery procedure (summary) | Target time |
|---|---|---|---|---|
| DRP-NAV-001-S01 | Backend process crash / host loss | `GET /health` fails or times out; frontend shows "API unreachable: …" | Rebuild host from Git at the release commit, reinstall, restart uvicorn | 30 min |
| DRP-NAV-001-S02 | Bad release (regression merged to `main`) | CI red on `main` push, or §7 verification fails after deployment | Revert the merge commit through a PR (SOP-IT-002 §5.4), redeploy last good commit | 1 h |
| DRP-NAV-001-S03 | Curated data lost, corrupted or mis-pointed (`data/*.parquet` deleted/damaged, wrong `NAVIGATOR_DATA_DIR`) | Start-up fails with `FileNotFoundError: navigator data directory not found` / `missing curated table`, or `/health` `row_counts` differ from §7 | Restore `data/` from Git or regenerate with `data/generate.py`; verify table equality; restart | 1 h |
| DRP-NAV-001-S04 | Git host / repository unavailable | `git clone`/`fetch` fails; GitHub status page | Restore from off-platform mirror or bundle (GAP-02), rebuild per S01 | 4 h |
| DRP-NAV-001-S05 | Package registry outage or dependency drift (PyPI/npm unavailable, or a new upstream release breaks the build) | `pip install` / `npm ci` fails, or tests fail with no code change | Install from local wheel/npm cache or pin to the versions of the last green CI run; `npm ci` uses the lockfile | 4 h |
| DRP-NAV-001-S06 | Frontend build or static assets unavailable | Page does not load, or `npm run build` fails | Rebuild with `npm ci && npm run build`; serve via Vite with `/api` proxy | 1 h |

## 6. Recovery procedures

All commands run from a clean checkout of the repository root unless stated. `<release>` = the commit recorded as the
current validated state (v0.1: `20e748e39c98d163c6d1f6fc2398254b3916d3f4`). Record start/end time, operator and
results of §7 in the DR log (Jira comment on the incident ticket).

### 6.1 S01 — Backend process crash / host loss

1. `git clone https://github.com/amitmanchella-cog/gsk-scale-ai-demo.git && cd gsk-scale-ai-demo`
2. `git checkout <release>`
3. `python3 -m venv .venv && . .venv/bin/activate` (Python ≥ 3.10; 3.11 matches CI)
4. `pip install -r apps/navigator/backend/requirements.txt`
5. Set configuration if non-default: `export NAVIGATOR_CORS_ORIGINS=<origins>`; leave `NAVIGATOR_DATA_DIR` unset to
   use `<repo root>/data`.
6. `uvicorn app.main:app --app-dir apps/navigator/backend --host 0.0.0.0 --port 8000`
7. Run §7.1 and §7.2.

### 6.2 S02 — Bad release

1. Identify the offending merge commit `<bad>` on `main` (`git log --oneline -- apps/navigator data`).
2. `git checkout -b revert/<bad> origin/main && git revert -m 1 <bad>` (never commit to `main` directly).
3. Push and open a PR linked to an emergency change ticket (SOP-IT-002 §5.1, *Emergency* → retrospective CCR within
   5 working days); CI must be green; merge by an approver other than the author.
4. Redeploy the new `main` head per §6.1 steps 2–7.
5. Note: reverting `20e748e` itself removes the Navigator entirely — for v0.1 prefer reverting only later changes.

### 6.3 S03 — Curated data lost / corrupted / mis-pointed

1. Check configuration: `echo "$NAVIGATOR_DATA_DIR"` — unset it or correct it (absolute path, or relative to repo root).
2. Restore from Git: `git checkout <release> -- data/*.parquet`
   **or** regenerate to a directory: `python data/generate.py --out <dir>` then `export NAVIGATOR_DATA_DIR=<dir>`
   (needs `pandas` + `pyarrow`, already installed by §6.1 step 4).
3. If regenerated, prove equality with the committed tables:
   ```bash
   python - <<'PY'
   import pandas as pd
   for t in ["hcps", "visits", "follow_ups", "reps", "territories", "weekly_sales"]:
       a = pd.read_parquet(f"data/{t}.parquet"); b = pd.read_parquet(f"<dir>/{t}.parquet")
       print(t, len(a), a.equals(b))   # every line must end in True
   PY
   ```
4. Restart the backend (§6.1 step 6) — tables are read only at start-up (`lifespan` → `load_tables()`).
5. Run §7.1–§7.3.

### 6.4 S04 — Git host / repository unavailable

1. Obtain the latest off-platform copy (GAP-02): `git clone <mirror-url> gsk-scale-ai-demo` or
   `git clone gsk-scale-ai-demo.bundle gsk-scale-ai-demo`.
2. Confirm the release commit is present: `git cat-file -e <release>^{commit} && echo present`.
3. Continue with §6.1 steps 2–7 (and §6.5 if registries are also unavailable).
4. When the Git host returns, compare `main` heads before resuming normal change control.

### 6.5 S05 — Registry outage / dependency drift

1. Backend: `pip download -r apps/navigator/backend/requirements.txt -d wheels/` from a host with access (or use an
   existing cache), then `pip install --no-index --find-links wheels/ -r apps/navigator/backend/requirements.txt`.
2. If a new upstream release broke the build, pin to the versions from the last green CI run's install log
   (`pip install fastapi==<v> …`) and raise a change ticket to add a constraints file (GAP-04).
3. Frontend: `npm ci` (lockfile-pinned); with no registry access use an offline cache
   (`npm ci --offline` with a pre-populated `~/.npm`).
4. Run §7.

### 6.6 S06 — Frontend build / assets unavailable

1. `cd apps/navigator/frontend` (Node ≥ 20; `nvm install 20 && nvm use 20` if needed)
2. `npm ci && npm run build` (output in `dist/`)
3. Serve: `VITE_API_BASE=http://<backend-host>:8000 npm run dev` (port 5173, proxies `/api/*` to the backend).
   No production web server is defined at `20e748e` (GAP-01).
4. Run §7.4.

## 7. Verification after recovery

| Step | Check | Expected result | Automated equivalent (test / CI job) |
|---|---|---|---|
| 7.1 | `curl -s http://<host>:8000/health` | `"status":"ok"`, `"version":"0.1.0"`, `row_counts` = `hcps` 1600, `visits` 4611, `follow_ups` 1393, `reps` 30, `territories` 20, `weekly_sales` 2080; `data_dir` = intended directory | `apps/navigator/backend/tests/test_endpoints.py::test_health_reports_row_counts` |
| 7.2 | `curl -s http://<host>:8000/reps` and `/territories` | 30 reps sorted by `rep_id`, first `R001` / `T001` / `South`; 20 territories, first `T001` `South-01` | `test_endpoints.py::test_list_reps`, `test_endpoints.py::test_list_territories` |
| 7.3 | Data integrity | All 6 tables load; regenerated tables equal committed ones (§6.3 step 3) | `apps/navigator/backend/tests/test_data.py::test_load_tables_reads_all_tables`, `data/tests/test_generate.py::test_generator_is_deterministic`, `::test_referential_integrity` |
| 7.4 | Frontend | `GET /` title "Field Force Navigator"; `GET /api/health` via the Vite proxy returns 7.1 payload; page shows "API ok" and "Reps (30)" | `apps/navigator/frontend/src/App.test.tsx` ("renders the title and lists reps from the API", "shows an error when the API is unreachable") |
| 7.5 | Full regression | `pytest apps/navigator/backend data/tests` → 18 passed; `npm run lint`, `npm test -- --run` (2 passed), `npm run build` succeed | CI jobs `python` and `navigator-frontend` on the recovered commit (baseline run: https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41018019513 — both jobs `success` at `20e748e`) |

Recovery is complete only when 7.1–7.5 pass and the result is recorded in the DR log.

## 8. Roles, contacts and escalation

Roles only (no names) in this demo.

| Role | Responsibility in DR |
|---|---|
| DR Coordinator (System Owner or delegate) | Declares the disaster, selects the scenario, approves return to service |
| Recovery Engineer (Change Owner; may be Devin under a playbook) | Executes §6 and §7, records evidence |
| Technical Reviewer | Confirms §7 results match this plan and the validated commit |
| Quality Assurance | Assesses impact on validated state; approves emergency CCR (SOP-IT-002 §5.1) |
| Repository / platform administrator | Restores Git access, mirrors, CI runners (S04, S05) |

Escalation: Recovery Engineer → DR Coordinator (immediately on detection) → QA (if RTO at risk or validated state
in doubt, within 4 h) → System Owner for business decision when MTD (5 working days) is at risk.

## 9. DR test plan and schedule

### 9.1 Tests

| Test ID | Scenarios | Method | Pass criteria |
|---|---|---|---|
| DRP-NAV-001-T01 | S01, S06 | Technical restore from a clean clone at `<release>` on a fresh host | §7.1, 7.2, 7.4, 7.5 pass; elapsed ≤ 30 min |
| DRP-NAV-001-T02 | S03 | Delete `data/`, regenerate with `data/generate.py`, point `NAVIGATOR_DATA_DIR`, restart | §6.3 step 3 all `True`; §7.1, 7.3 pass; also confirm missing-dir start-up fails with `FileNotFoundError` |
| DRP-NAV-001-T03 | S02 | Tabletop: walk through revert PR flow on a throwaway branch | Steps in §6.2 are executable; CI green on revert PR |
| DRP-NAV-001-T04 | S04, S05 | Tabletop until GAP-02/GAP-04 are closed, then technical | Mirror/bundle and offline install restore the release commit |

### 9.2 Schedule

- Before v1.0 approval: T01 and T02 witnessed by the Technical Reviewer.
- Every 12 months, after any infrastructure / deployment / backup change (SOP-IT-002 §6), and before release of the
  weekly plan builder (PRD feature 3).
- Continuous: every PR's CI rebuilds the system from a clean checkout (`python`, `navigator-frontend`).

### 9.3 Author's pre-review drill (informative, not a substitute for T01/T02)

Executed 2026-10-30 by the author in an isolated worktree detached at `20e748e39c98d163c6d1f6fc2398254b3916d3f4`:

- `pip install -r apps/navigator/backend/requirements.txt`; `pytest apps/navigator/backend data/tests` → `18 passed`.
- `python data/generate.py --out <tmp>`; equality check (§6.3 step 3) → all 6 tables `True` (1600/4611/1393/30/20/2080 rows).
- `NAVIGATOR_DATA_DIR=<tmp> uvicorn app.main:app --app-dir apps/navigator/backend` → `/health` `status ok`,
  version `0.1.0`, row counts as §7.1, `data_dir` = `<tmp>`; `/reps` 30 (first `R001 Dev Okafor T001 South`);
  `/territories` 20.
- `NAVIGATOR_DATA_DIR=<missing dir>` → start-up fails with `FileNotFoundError: navigator data directory not found`.
- Frontend: `npm ci`, `npm run lint` clean, `vitest --run` → `2 passed`, `npm run build` → built; Vite dev server
  `GET /api/health` → 7.1 payload, `GET /` title "Field Force Navigator". (Local Node was v24; CI uses Node 20.)

## 10. Traceability matrix

DRP-level recovery requirements (`DRP-NAV-001-Rnn`) are derived from the change (PR #8 at `20e748e`) and the PRD.
They are to be cross-referenced to the URS-NAV-001 requirement IDs at review (GAP-05).

| Req ID | Requirement (short) | Source (ticket / PRD §) | Design ref | Code path(s) | Test(s) | Change ref (ticket / PR) | Status |
|---|---|---|---|---|---|---|---|
| DRP-NAV-001-R01 | Health endpoint detects outage and reports per-table row counts | MBA-3680; PR #8 "Endpoints" | §5 S01/S03 detection, §7.1 | `apps/navigator/backend/app/main.py` (`health`), `app/models.py` (`Health`) | `apps/navigator/backend/tests/test_endpoints.py::test_health_reports_row_counts` | MBA-3680 / PR #8 | Verified |
| DRP-NAV-001-R02 | Curated data restorable to identical state (RPO = last merge) | MBA-3680; PRD "Data" | §2 RPO, §4, §6.3 | `data/generate.py` (`generate`, `SEED = 42`), `apps/navigator/backend/app/data.py` (`load_tables`) | `data/tests/test_generate.py::test_generator_is_deterministic`, `apps/navigator/backend/tests/test_data.py::test_load_tables_reads_all_tables` | MBA-3680 / PR #8 | Verified |
| DRP-NAV-001-R03 | Data location configurable for restore to an alternate directory | PR #8 "Layout" (`NAVIGATOR_DATA_DIR`) | §3, §6.3 step 2 | `apps/navigator/backend/app/data.py` (`resolve_data_dir`, `DATA_DIR_ENV`) | `test_data.py::test_env_override`, `test_data.py::test_relative_override_resolves_against_repo_root`, `test_data.py::test_default_data_dir_is_repo_root_data` | MBA-3680 / PR #8 | Verified |
| DRP-NAV-001-R04 | Missing/incorrect data fails fast at start-up (no silent empty service) | PR #8 `app/data.py` | §5 S03 detection, §9.1 T02 | `apps/navigator/backend/app/data.py` (`load_tables` → `FileNotFoundError`) | `test_data.py::test_load_tables_missing_dir` | MBA-3680 / PR #8 | Verified (missing directory; missing single table: GAP — add test for `missing curated table`) |
| DRP-NAV-001-R05 | Reps and territories served correctly after recovery | MBA-3680; PR #8 "Endpoints" | §7.2 | `apps/navigator/backend/app/main.py` (`list_reps`, `list_territories`) | `test_endpoints.py::test_list_reps`, `test_endpoints.py::test_list_territories` | MBA-3680 / PR #8 | Verified |
| DRP-NAV-001-R06 | Frontend rebuildable and surfaces backend outage to the user | MBA-3680; PR #8 frontend | §5 S01/S06, §6.6, §7.4 | `apps/navigator/frontend/src/App.tsx`, `src/api.ts` (`getJson`), `vite.config.ts` (`/api` proxy) | `apps/navigator/frontend/src/App.test.tsx` ("renders the title and lists reps from the API", "shows an error when the API is unreachable") | MBA-3680 / PR #8 | Verified |
| DRP-NAV-001-R07 | CORS origins restorable from configuration | PR #8 README "CORS" | §3, §6.1 step 5 | `apps/navigator/backend/app/main.py` (`cors_origins`, `DEFAULT_CORS_ORIGINS`) | `test_endpoints.py::test_cors_allows_vite_dev_server` (default origins) | MBA-3680 / PR #8 | Partially verified — GAP: no test for `NAVIGATOR_CORS_ORIGINS` override |
| DRP-NAV-001-R08 | System rebuildable and verifiable from a clean checkout by CI | MBA-3680; PR #8 "CI" | §4, §7.5, §9.2 | `.github/workflows/ci.yml` (jobs `python`, `navigator-frontend`) | CI run 41018019513 at `20e748e` (both jobs success) | MBA-3680 / PR #8 | Verified |
| DRP-NAV-001-R09 | Territory HCP list with filters and search (recovery of HCP view) | PRD "In scope" feature 1, AC1 | §1 (future scope) | GAP — not implemented at `20e748e` (no HCP endpoint) | GAP — no test; add when implemented | MBA-3680 / PR #8 | Not implemented in this change |
| DRP-NAV-001-R10 | Visit priority score; configurable rules restorable with the system | PRD feature 2, AC2, AC3 | §3 configuration (future) | GAP — not implemented at `20e748e` (no scoring module or rule config) | GAP — no test; PRD NFR ≥ 90 % coverage applies when implemented | MBA-3680 / PR #8 | Not implemented in this change |
| DRP-NAV-001-R11 | Weekly plans (rep-created records) backed up and restorable | PRD feature 3, AC4, AC5 | §2 RPO, §4 records row | GAP — not implemented at `20e748e`; first feature creating records → needs persistent store, backup and revised RPO (GAP-03) | GAP — no test | MBA-3680 / PR #8 | Not implemented in this change |
| DRP-NAV-001-R12 | Plan CSV export available after recovery | PRD feature 3, AC6 | §7 (future check) | GAP — not implemented at `20e748e` (no export endpoint) | GAP — no test | MBA-3680 / PR #8 | Not implemented in this change |
| DRP-NAV-001-R13 | Container image as restorable build artefact | PRD "Non-functional" (container build on every PR) | §3 build artefacts | GAP — no Dockerfile or container CI job at `20e748e` (GAP-01) | GAP — no container build/smoke test | MBA-3680 / PR #8 | Not implemented in this change |
| DRP-NAV-001-R14 | HCP list loads < 1 s for 300 HCPs (post-recovery performance check) | PRD "Non-functional" | §7 (future check) | GAP — HCP list not implemented at `20e748e` | GAP — no performance test | MBA-3680 / PR #8 | Not implemented in this change |
| DRP-NAV-001-R15 | Basic keyboard accessibility preserved after rebuild | PRD "Non-functional" | §7.4 (future check) | GAP — placeholder page only at `20e748e`; no interactive controls | GAP — no accessibility test | MBA-3680 / PR #8 | Not implemented in this change |

### Open gaps

| Gap ID | Gap | Action / owner |
|---|---|---|
| GAP-01 | No hosted environment, container image or deployment pipeline at `20e748e`; recovery is a source rebuild | Update this DRP (and FS-NAV-001) when a Dockerfile / deploy workflow is introduced — System Owner |
| GAP-02 | No off-platform repository mirror or bundle configured; S04 depends on it | Configure scheduled `git clone --mirror` / `git bundle` to independent storage — Platform administrator |
| GAP-03 | PRD weekly plan builder will create rep records; no persistence/backup design yet | Design persistent store + backup, revise RPO/criticality, add Annex 11 §7 controls before release — System Owner / QA |
| GAP-04 | Backend `requirements.txt` uses lower bounds only; rebuild may pull different versions | Add a constraints/lock file captured from green CI — Change Owner |
| GAP-05 | Cross-reference DRP-NAV-001-Rnn to URS-NAV-001 IDs (drafted in parallel) | Technical Reviewer at review |
| GAP-06 | Tests missing for `missing curated table` path and `NAVIGATOR_CORS_ORIGINS` override (R04, R07) | Add tests under a change ticket — Change Owner |
| GAP-07 | `docs/gxp/ESTATE_MAP.md` §2 names the NAV CI job `frontend`; the actual job id is `navigator-frontend` | Correct the estate map in the baseline — baseline owner (QA) |

## 11. Impact on validated state

- Validated state before change: none for NAV — Field Force Navigator enters the validated estate with this change;
  proposed first baseline = commit `20e748e39c98d163c6d1f6fc2398254b3916d3f4` + URS-NAV-001, FS-NAV-001,
  DRP-NAV-001, CCR-NAV-001.
- Components affected: `apps/navigator/backend` (`app/main.py`, `app/data.py`, `app/models.py`),
  `apps/navigator/frontend` (`src/App.tsx`, `src/api.ts`, `vite.config.ts`), CI job `navigator-frontend` (new) and
  `python` (now also runs navigator tests), upstream data `data/*.parquet` (read-only consumer).
- GxP impact assessment: Indirect — the system presents HCP interaction data used for field-force planning
  (compliance-relevant) but makes no product-quality or patient-safety decision; v0.1 exposes only reps and
  territories. Consistent with ESTATE_MAP §2 and MBA-3680.
- Data integrity (ALCOA+) impact: none on records — v0.1 creates, modifies or deletes no data (all endpoints `GET`).
  Source data remains original and complete in Git; recovery fidelity is demonstrated by table equality (§6.3, §9.3).
- Part 11 / Annex 11 controls affected: backups (Annex 11 §7.2) — provided by Git + deterministic regeneration
  (§4), restore verified (§9.3); business continuity (§16) — this plan; audit trail — N/A (no records; Git history is
  the change audit trail); e-signatures — PR approvals per SOP-QA-001 §6; access control — GitHub repository
  permissions (no application-level authentication in v0.1, SSO out of scope per PRD).
- Revalidation required: N/A — initial validation. DR tests T01 and T02 (§9.1) to be executed and witnessed before
  v1.0 approval. Any later change hitting GAP-01/GAP-03 triggers a DRP update (SOP-IT-002 §6 "Infrastructure /
  deployment / backup change").
- Other controlled documents to update: URS-NAV-001 (cross-reference GAP-05), FS-NAV-001 (inventory/config in §3
  must match), CCR-NAV-001 (lists DRP-NAV-001 v0.1 as an affected document).

## 12. Revision history

| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
| 0.1 DRAFT | 2026-10-30 | Devin (AI-drafted, playbook GxP controlled document from change) | [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680) / PR [#8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8) (`20e748e`) | First draft for QA review: DR plan for Navigator v0.1 scaffold; PRD features listed as not implemented with gaps |
