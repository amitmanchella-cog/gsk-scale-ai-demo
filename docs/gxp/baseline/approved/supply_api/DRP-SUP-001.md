# DRP-SUP-001 — Clinical Supply Forecast API: Disaster Recovery Plan

> **Approved past document (style reference).** Synthetic, written for the GSK Scale AI demo; no real GSK data.

| Field | Value |
|---|---|
| Document ID | DRP-SUP-001 |
| Version | 1.0 (Approved) |
| System | Clinical Supply Forecast API (`services/supply_api`) |
| GAMP 5 category / GxP impact | 5 / Indirect |
| Change reference | PR #1 (https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/1), merge commit cf550c9 |
| Governing SOPs | SOP-QA-001, SOP-IT-002 |

## Approvals
| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | A. Engineer (synthetic) | Authored and technically accurate | e-signed 2026-10-22 |
| System Owner | S. Owner (synthetic) | Recovery objectives accepted | e-signed 2026-10-22 |
| Technical Reviewer | T. Reviewer (synthetic) | Procedures executable at cf550c9 | e-signed 2026-10-23 |
| Quality Assurance | Q. Approver (synthetic) | Complies with SOP-QA-001 | e-signed 2026-10-23 |

## 1. Purpose and scope
Recovery of the supply_api service (all environments). v1 is stateless apart from in-memory synthetic data.

## 2. Criticality and recovery objectives
| Item | Value | Rationale |
|---|---|---|
| Business criticality | Medium | Planning aid; planners can fall back to last exported plan |
| RTO | 4 h | Rebuild from Git + redeploy is < 30 min |
| RPO | Last merge commit on `main` | No persisted state; seeded data regenerated deterministically (seed 42) |

## 3. System inventory for recovery
Source: `services/supply_api` at the release commit · Runtime: Python 3.11, `requirements.txt` · Config: none ·
Data: generated at start-up by `app/data.py` · Secrets: none.

## 5. Disaster scenarios
| Scenario ID | Scenario | Detection | Recovery (summary) | Target |
|---|---|---|---|---|
| DRP-SUP-001-S01 | Process crash / host loss | `GET /health` fails | Redeploy from `main` | 30 min |
| DRP-SUP-001-S02 | Bad release | CI or smoke test fails post-merge | Revert merge commit, redeploy | 1 h |
| DRP-SUP-001-S03 | Repository unavailable | Git host outage | Restore from mirror / last release artefact | 4 h |

## 6. Recovery procedures (S01)
1. `git checkout <release commit>` · 2. `pip install -r services/supply_api/requirements.txt` ·
3. `uvicorn app.main:app --app-dir services/supply_api` · 4. run §7.

## 7. Verification after recovery
`curl /health` → `{"status":"ok"}`; `pytest services/supply_api` → 34 passed; `GET /sites` → 8 sites.

## 9. DR test plan
Restore drill every 12 months and after any infrastructure change (SOP-IT-002 §6).

## 10. Traceability matrix
| Req ID | Requirement (short) | Source | Design ref | Code path(s) | Test(s) | Change ref | Status |
|---|---|---|---|---|---|---|---|
| URS-SUP-001-R01 | Health check (detection) | URS-SUP-001 | S01 | `app/main.py` (`/health`) | `test_health` | PR #1 | Verified |
| URS-SUP-001-R02 | Deterministic seeded data (RPO) | URS-SUP-001 | §3 | `app/data.py` | `test_list_sites`, `test_list_products` | PR #1 | Verified |

## 11. Impact on validated state
New plan; no change to system validated state. Revalidation: none. Part 11/Annex 11 §7 backups: N/A (no records).

## 12. Revision history
| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
| 1.0 | 2026-10-23 | A. Engineer | PR #1 | Approved |
