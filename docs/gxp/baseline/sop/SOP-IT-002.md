# SOP-IT-002 — Change Control for Validated Computerised Systems

| Field | Value |
|---|---|
| Document ID | SOP-IT-002 |
| Version | 3.1 (Approved) |
| Owner | IT Quality & Compliance |
| References | GAMP 5 (2nd ed.) §O6 Change Management, 21 CFR Part 11, EU GMP Annex 11 §10, ICH Q9, SOP-QA-001 |

> Synthetic SOP written for the GSK Scale AI demo. Not a real GSK procedure.

## 1. Purpose
Ensure every change to a validated system is requested, assessed, approved, tested, documented and reviewed so the
system stays in a validated state (Annex 11 §10).

## 2. Scope
Code, configuration, infrastructure and data-model changes to systems listed in `docs/gxp/ESTATE_MAP.md`.

## 3. Definitions
- **Change** — any ticket, PR or release that alters a validated system. **Validated state** — the approved baseline
  (commit + controlled documents) at which the system was last verified.

## 4. Responsibilities
Change Requester (raises the ticket) · Change Owner (implements; may be Devin under a playbook) · System Owner
(approves) · QA (approves GxP-impacting changes, closes the CCR).

## 5. Procedure
1. **Request** — a Jira ticket in the system's project with description, justification and affected system.
   Change types: *Standard* (pre-approved, low risk), *Normal* (assessed per change), *Emergency* (retrospective CCR
   within 5 working days).
2. **Impact assessment** — classify GxP impact, run a risk assessment (ICH Q9: severity × probability ×
   detectability) and list the controlled documents affected (§6).
3. **Approve to implement** — System Owner (+ QA if GxP impact is Direct/Indirect).
4. **Implement** — on a branch, through a PR linked to the ticket; never commit directly to `main`.
5. **Verify** — CI green (lint + automated tests); evidence recorded in the CCR.
6. **Document** — create/update the controlled documents in §6 under SOP-QA-001 before release.
7. **Release** — merge by an approver other than the author; record the merge commit in the CCR.
8. **Close** — post-implementation review; QA closes the CCR.

## 6. Controlled documents required per change
| Change | URS | FS | DRP | CCR |
|---|---|---|---|---|
| New validated system / major version | Create | Create | Create | Create |
| New or changed user-facing function | Update | Update | Review | Create |
| Infrastructure / deployment / backup change | — | Update | Update | Create |
| Bug fix, no requirement change | — | Review | — | Create |

## 7. Records
Ticket, PR (diff, reviews, CI checks), CCR and the updated controlled documents. Retained for the life of the system
plus 5 years. In this demo, Git + Jira are the systems of record.

## 8. Change control checklist (attach to every CCR)
| # | Check |
|---|---|
| C1 | Ticket exists and links the PR(s); PR links the ticket |
| C2 | Change type and GxP impact classified with rationale |
| C3 | Risk assessment recorded with mitigations |
| C4 | CI evidence (run URL, jobs, test counts) recorded |
| C5 | Affected controlled documents listed with DOC-ID + version, each with its own PR |
| C6 | Author ≠ approver; merge commit recorded |
| C7 | Back-out plan stated |

## 9. Revision history
| Version | Date | Author | Description |
|---|---|---|---|
| 3.0 | 2025-06-12 | IT Q&C | Git/PR as change record |
| 3.1 | 2026-10-30 | IT Q&C | §6 matrix; agent-implemented changes (Devin under playbook) |
