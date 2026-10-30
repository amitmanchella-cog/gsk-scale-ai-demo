# CCR-SUP-001 — Change Control Record: introduce Clinical Supply Forecast API v1

> **Approved past document (style reference).** Synthetic, written for the GSK Scale AI demo; no real GSK data.

| Field | Value |
|---|---|
| Document ID | CCR-SUP-001 |
| Document type | CCR |
| Version | 1.0 (Approved — closed) |
| System | Clinical Supply Forecast API (`services/supply_api`) |
| GAMP 5 category | 5 |
| GxP impact | Indirect |
| Change reference | PR #1 (https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/1), merge commit cf550c9 |
| Author | Supply Systems Engineering |
| Governing SOPs | SOP-IT-002, SOP-QA-001 |

## Approvals
| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | A. Engineer (synthetic) | Authored and technically accurate | e-signed 2026-10-21 |
| System Owner | S. Owner (synthetic) | Change approved for release | e-signed 2026-10-22 |
| Technical Reviewer | T. Reviewer (synthetic) | Evidence matches CI at cf550c9 | e-signed 2026-10-22 |
| Quality Assurance | Q. Approver (synthetic) | Complies with SOP-IT-002; CCR closed | e-signed 2026-10-23 |

## 1. Change summary
| Field | Value |
|---|---|
| Change title | Add supply_api clinical supply forecast service |
| Change type | Normal (new validated system) |
| Pull request(s) | PR #1, merge commit cf550c9 |
| Release / version | supply_api 0.1.0 |
| Environments | CI → main |

## 2. Description and justification
New FastAPI service giving planners forecasts and reorder recommendations, replacing spreadsheet planning (synthetic).

## 3. Scope of change
`services/supply_api/**` (app, tests, README), `.github/workflows/ci.yml` (python job). No other system touched.

## 4. Risk assessment
| Risk ID | Hazard | Sev | Prob | Det | Class | Mitigation |
|---|---|---|---|---|---|---|
| CCR-SUP-001-K01 | Wrong site-local date shifts consumption into the wrong week | M | M | H | 2 | Timezone-aware parsing; 9 date/report tests |
| CCR-SUP-001-K02 | Forecast formula error under-orders supply | H | L | H | 2 | Pure-function forecast with exact-value tests; endpoint parity test |
| CCR-SUP-001-K03 | Data lost on restart | L | H | H | 3 | Accepted for v1 — in-memory synthetic data, not a record of truth |

## 5. Verification and testing evidence
| Evidence | Location | Result |
|---|---|---|
| CI `python` job (ruff + pytest) | PR #1 checks | Pass — 34 tests |
| Code review | PR #1 reviews | Approved |

## 6. Implementation and back-out plan
Merge PR #1. Back-out: revert merge commit cf550c9 (service is additive, no data migration).

## 7. Controlled documents created or updated
URS-SUP-001 v1.0 · FS-SUP-001 v1.0 · CCR-SUP-001 v1.0 (this record).

## 8. Post-implementation review and closure
CI green on main after merge; no incidents. Closed by QA 2026-10-23.

## 9. Traceability matrix
| Req ID | Requirement (short) | Source | Design ref | Code path(s) | Test(s) | Change ref | Status |
|---|---|---|---|---|---|---|---|
| URS-SUP-001-R05 | Forecast | URS-SUP-001 | FS-SUP-001-F05 | `services/supply_api/app/forecast.py` | `test_forecast.py` | PR #1 | Verified |
| URS-SUP-001-R08 | Site-local dates | URS-SUP-001 | FS-SUP-001-F08 | `services/supply_api/app/dates.py` | `test_dates_and_reports.py` | PR #1 | Verified |
| (R01–R04, R06–R07) | see URS-SUP-001 §7 | URS-SUP-001 | FS-SUP-001 | `services/supply_api/app/main.py` | `test_health_and_catalog.py`, `test_reorder.py`, `test_shipments.py` | PR #1 | Verified |

## 10. Impact on validated state
New system → validated state established at cf550c9. Revalidation: full initial. Part 11 audit trail N/A (no
persisted records). Other documents: URS-SUP-001, FS-SUP-001.

## SOP-IT-002 §8 checklist
- [x] C1 ticket/PR linked · [x] C2 classified · [x] C3 risk assessed · [x] C4 CI evidence · [x] C5 documents listed
- [x] C6 author ≠ approver · [x] C7 back-out plan

## 11. Revision history
| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
| 1.0 | 2026-10-23 | A. Engineer | PR #1 | Approved and closed |
