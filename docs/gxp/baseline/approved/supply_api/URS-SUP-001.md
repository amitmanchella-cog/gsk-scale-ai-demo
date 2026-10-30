# URS-SUP-001 — Clinical Supply Forecast API: User Requirements Specification

> **Approved past document (style reference).** Synthetic, written for the GSK Scale AI demo; no real GSK data.

| Field | Value |
|---|---|
| Document ID | URS-SUP-001 |
| Document type | URS |
| Version | 1.0 (Approved) |
| Status | Approved |
| System | Clinical Supply Forecast API (`services/supply_api`) |
| GAMP 5 category | 5 (custom application) |
| GxP impact | Indirect — supports clinical supply planning (GCP/GDP), no direct patient or batch-release decision |
| Change reference | UC3 initial delivery, PR #1 (https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/1), merge commit cf550c9 |
| Author | Supply Systems Engineering |
| Effective date | 2026-10-23 |
| Governing SOPs | SOP-QA-001, SOP-IT-002 |

## Approvals
| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | A. Engineer (synthetic) | Authored and technically accurate | e-signed 2026-10-21 |
| System Owner | S. Owner (synthetic) | Content fit for intended use | e-signed 2026-10-22 |
| Technical Reviewer | T. Reviewer (synthetic) | Matches the code and tests at cf550c9 | e-signed 2026-10-22 |
| Quality Assurance | Q. Approver (synthetic) | Complies with SOP-QA-001 and the template | e-signed 2026-10-23 |

## 1. Purpose and scope
Provide clinical supply planners with an API for site/product catalogue, stock, weekly consumption, forecasts,
reorder recommendations, shipments and a consumption report across 8 trial sites and 6 investigational products.
Out of scope: authentication, persistence beyond process memory, integration with IRT/ERP.

## 2. Regulatory context and system classification
GAMP 5 Category 5. GxP impact Indirect. 21 CFR Part 11 / Annex 11 apply to records once persisted; v1 holds data in
memory only (see §8). Data: synthetic, deterministic (seed 42).

## 3. References
`services/supply_api/README.md`, PR #1, SOP-QA-001, SOP-IT-002.

## 4. User requirements
| Req ID | Category | Requirement | Acceptance criterion | Priority | Source |
|---|---|---|---|---|---|
| URS-SUP-001-R01 | Availability | The service exposes a health check | `GET /health` returns 200 `{"status":"ok"}` | M | PR #1 |
| URS-SUP-001-R02 | Data | Planners can list sites and products | `GET /sites` returns 8 sites with IANA timezone; `GET /products` returns 6 products; unknown id → 404 | M | PR #1 |
| URS-SUP-001-R03 | Data | Planners can view stock, filterable by site/product | `GET /stock` filters correctly; unknown filter → 404 | M | PR #1 |
| URS-SUP-001-R04 | Functional | Planners can view weekly consumption history | `GET /consumption/{site}/{product}?weeks=n` returns the n most recent weeks, default full 26 | M | PR #1 |
| URS-SUP-001-R05 | Functional | The system forecasts weekly consumption | Moving-average (window 4) and linear-trend methods; default horizon 4 weeks; invalid input → 422 | M | PR #1 |
| URS-SUP-001-R06 | Functional | The system recommends reorders | Quantity follows the documented lead-time formula (default lead time 6 weeks) | M | PR #1 |
| URS-SUP-001-R07 | Functional | Planners can record and list shipments | `POST /shipments` round-trips via `GET /shipments`; unknown site/product → 404; invalid payload → 422 | M | PR #1 |
| URS-SUP-001-R08 | Data integrity | Date ranges are interpreted in each site's local time | Offset/`Z` timestamps accepted, naive rejected (422); report uses site-local dates (Tokyo next-day case) | M | PR #1 |

## 5. Data integrity (ALCOA+)
Attributable: N/A v1 (no users) — **GAP** tracked for v2 (auth). Accurate: deterministic seed + unit tests.
Original/Enduring: in-memory only — v1 not used as a record of truth. Consistent: timezone-aware dates (R08).

## 6. Constraints and assumptions
Python 3.11+, FastAPI; single process; synthetic data only.

## 7. Traceability matrix
| Req ID | Requirement (short) | Source | Design ref | Code path(s) | Test(s) | Change ref | Status |
|---|---|---|---|---|---|---|---|
| R01 | Health check | PR #1 | FS-SUP-001-F01 | `services/supply_api/app/main.py` (`/health`) | `test_health_and_catalog.py::test_health` | PR #1 | Verified |
| R02 | Sites / products | PR #1 | FS-SUP-001-F02 | `app/main.py`, `app/data.py` | `test_list_sites`, `test_get_site`, `test_get_site_unknown_404`, `test_list_products` | PR #1 | Verified |
| R03 | Stock | PR #1 | FS-SUP-001-F03 | `app/main.py` (`/stock`) | `test_stock_unfiltered_and_filtered`, `test_stock_unknown_filter_404` | PR #1 | Verified |
| R04 | Consumption | PR #1 | FS-SUP-001-F04 | `app/main.py` (`/consumption`) | `test_consumption_history_most_recent_weeks`, `test_consumption_defaults_to_full_history`, `test_consumption_validation` | PR #1 | Verified |
| R05 | Forecast | PR #1 | FS-SUP-001-F05 | `app/forecast.py` | `test_forecast.py` (7 tests) | PR #1 | Verified |
| R06 | Reorder | PR #1 | FS-SUP-001-F06 | `app/main.py` (`/reorder`) | `test_reorder.py` (4 tests) | PR #1 | Verified |
| R07 | Shipments | PR #1 | FS-SUP-001-F07 | `app/main.py` (`/shipments`) | `test_shipments.py` (4 tests) | PR #1 | Verified |
| R08 | Site-local dates | PR #1 | FS-SUP-001-F08 | `app/dates.py`, `app/main.py` (`/reports/consumption`) | `test_dates_and_reports.py` (9 tests) | PR #1 | Verified |

## 8. Impact on validated state
- Validated state before change: none (new system). After: v1.0 at cf550c9.
- GxP impact Indirect; data integrity: in-memory synthetic data, not a record of truth.
- Part 11 / Annex 11: audit trail and e-signatures N/A for v1 (no persisted records) — reassess when persistence is added.
- Revalidation: Full initial validation (CI: 34 automated tests). Other documents: FS-SUP-001, CCR-SUP-001.

## 9. Revision history
| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
| 0.1 | 2026-10-21 | A. Engineer | PR #1 | Draft |
| 1.0 | 2026-10-23 | A. Engineer | PR #1 | Approved after QA review |
