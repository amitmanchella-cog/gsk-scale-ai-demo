# GxP estate map — validated systems in `gsk-scale-ai-demo`

> UC2 (GxP controlled-documentation compliance). Synthetic data only; nothing here is a real GSK system.
> Devin is managed infrastructure and governance (playbooks, Automations, ACU caps) that complements GSK's agentic
> factory: it maps the estate, drafts controlled documents per change and keeps them current, while humans approve.

Wiki view of the same estate: Devin Wiki https://devin-gtm.devinenterprise.com/wiki/amitmanchella-cog/gsk-scale-ai-demo (generated 2026-10-30) · public DeepWiki https://deepwiki.com/amitmanchella-cog/gsk-scale-ai-demo

## 1. Repositories

| Repo | Role | System of record for |
|---|---|---|
| [`amitmanchella-cog/gsk-scale-ai-demo`](https://github.com/amitmanchella-cog/gsk-scale-ai-demo) | Mono-repo for both validated systems, CI and controlled documents | Code, tests, controlled documents (`docs/gxp/controlled/**`), PR approvals = e-signatures |
| Jira project [MBA](https://cog-gtm.atlassian.net/jira/software/projects/MBA) | Change requests | Tickets (SOP-IT-002 §5.1) |

## 2. Validated systems and components

| SYS code | System | Path | GAMP 5 | GxP impact | Components | CI job |
|---|---|---|---|---|---|---|
| SUP | Clinical Supply Forecast API | `services/supply_api` | 5 | Indirect (clinical supply planning) | FastAPI app `app/main.py` (9 endpoints), `app/forecast.py` (moving average, linear trend), `app/dates.py` (timezone-aware parsing, site-local dates), `app/data.py` (seed-42 synthetic data: 8 sites, 6 products, 26 weeks), `app/models.py`; 34 pytest tests | `python` (ruff + pytest) |
| NAV | Field Force Navigator | `apps/navigator` | 5 | Indirect (HCP interaction records, compliance-relevant) | Backend FastAPI `backend/app/main.py` (`/health`, `/territories`, `/reps`), `backend/app/data.py` (reads UC1 parquet from `data/`, `NAVIGATOR_DATA_DIR`), `backend/app/models.py`; frontend React/Vite `frontend/src/App.tsx`; 9 backend + 2 frontend tests | `python`, `navigator-frontend` (lint, vitest, build) |

Upstream data dependency: NAV reads the curated tables produced by UC1 (`pipelines/territory_kpis`, `data/*.parquet`).

## 3. Requirements sources

| System | Source | What it holds |
|---|---|---|
| SUP | PR [#1](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/1), `services/supply_api/README.md` | Endpoint behaviour, data model, forecast/reorder rules |
| NAV | [`docs/uc4/PRD.md`](../uc4/PRD.md), PR [#8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8), `apps/navigator/README.md` | Territory Call Planner scope, acceptance criteria (scoring, 6 visits/day, Segment A overdue, CSV export), NFRs |

## 4. Controlled documents — exist vs missing

Baseline (templates, SOPs, approved references): [`docs/gxp/baseline/`](baseline/).

| System | URS | FS / Design Spec | DR plan | Change Control Record |
|---|---|---|---|---|
| SUP | ✅ URS-SUP-001 v1.0 ([approved](baseline/approved/supply_api/URS-SUP-001.md)) | ⚠️ FS-SUP-001 referenced but not in repo | ✅ DRP-SUP-001 v1.0 ([approved](baseline/approved/supply_api/DRP-SUP-001.md)) | ✅ CCR-SUP-001 v1.0 ([approved](baseline/approved/supply_api/CCR-SUP-001.md)) |
| NAV | ❌ missing (PRD only) | ❌ missing | ❌ missing | ❌ missing |

**Gap closed by the UC2 fleet:** change [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680) /
PR [#8](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8) (Navigator v0.1 scaffold) requires, per
SOP-IT-002 §6 "new validated system", URS-NAV-001, FS-NAV-001, DRP-NAV-001 and CCR-NAV-001. One Devin session per
document drafts each into `docs/gxp/controlled/navigator/<DOC-ID>.md` as its own docs-only PR for QA review.

## 5. Document ID register

| Prefix | Type | Template |
|---|---|---|
| URS | User Requirements Specification | [URS_TEMPLATE.md](baseline/templates/URS_TEMPLATE.md) |
| FS | Functional / Design Specification | [FS_TEMPLATE.md](baseline/templates/FS_TEMPLATE.md) |
| DRP | Disaster Recovery Plan | [DRP_TEMPLATE.md](baseline/templates/DRP_TEMPLATE.md) |
| CCR | Change Control Record | [CCR_TEMPLATE.md](baseline/templates/CCR_TEMPLATE.md) |

Next free numbers: SUP → FS-SUP-001 (missing), others 002; NAV → 001.

## 6. Change → document impact (who updates what on a merge)

| Paths changed in a merge | System | Documents to review/update (SOP-IT-002 §6) |
|---|---|---|
| `services/supply_api/app/**` | SUP | CCR (new) + URS/FS if behaviour changes |
| `services/supply_api/requirements.txt`, deployment | SUP | CCR + FS + DRP |
| `apps/navigator/backend/**`, `apps/navigator/frontend/**` | NAV | CCR (new) + URS/FS if behaviour changes |
| `data/**`, `pipelines/territory_kpis/**` | NAV (upstream) | CCR + FS (data model) |
| `docs/**` only | — | none |

This table is what the Automation in [`automation/`](automation/) uses to decide which documents to (re)draft.
