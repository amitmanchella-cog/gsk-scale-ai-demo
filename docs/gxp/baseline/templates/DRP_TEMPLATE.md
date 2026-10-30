# TEMPLATE — Disaster Recovery Plan (DRP)

Prefix `DRP`. Governing SOPs: SOP-QA-001, SOP-IT-002. Use the common header, approvals block and closing sections
from [`_COMMON_HEADER.md`](_COMMON_HEADER.md). Annex 11 §7 (data storage, backups) and §16 (business continuity).

## 1. Purpose and scope (system, environments covered)
## 2. Criticality and recovery objectives
| Item | Value | Rationale |
|---|---|---|
| Business criticality | High / Medium / Low | |
| RTO (recovery time objective) | | |
| RPO (recovery point objective) | | |
| Maximum tolerable downtime | | |
## 3. System inventory for recovery
Source repo + commit, build artefacts (container image / package), configuration, data stores, secrets (names only).
## 4. Backup and restore strategy (what, where, frequency, retention, restore test cadence)
## 5. Disaster scenarios
| Scenario ID | Scenario | Detection | Recovery procedure (summary) | Target time |
|---|---|---|---|---|
Use IDs `DRP-<SYS>-NNN-S<nn>`.
## 6. Recovery procedures (numbered, executable steps per scenario, with exact commands)
## 7. Verification after recovery (smoke tests, data integrity checks — name the test/CI job)
## 8. Roles, contacts and escalation (roles only in this demo)
## 9. DR test plan and schedule
## 10. Traceability matrix · 11. Impact on validated state · 12. Revision history
(see common closing sections)
