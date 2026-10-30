# SOP-QA-001 — Controlled Document Authoring & Review

| Field | Value |
|---|---|
| Document ID | SOP-QA-001 |
| Version | 2.0 (Approved) |
| Owner | Quality Assurance — Computerised Systems |
| Applies to | URS, FS, DRP, CCR and any controlled document for a validated system |
| References | GAMP 5 (2nd ed.), 21 CFR Part 11, EU GMP Annex 11, ICH Q9, SOP-IT-002 |

> Synthetic SOP written for the GSK Scale AI demo. Not a real GSK procedure.

## 1. Purpose
Define how controlled documents for validated computerised systems are authored, reviewed, approved and kept current,
including documents drafted by an AI agent (Devin).

## 2. Scope
All systems in the validated estate (`docs/gxp/ESTATE_MAP.md`). Applies to new documents and to updates triggered by
a change under SOP-IT-002.

## 3. Roles
- **Author** — drafts the document from the approved template. May be a human or Devin; an AI-drafted document names
  the playbook and session in the *Author* field and is never self-approved.
- **System Owner** — accountable for content fitness for intended use.
- **Technical Reviewer** — verifies the document matches the code, tests and configuration at the referenced commit.
- **Quality Assurance (QA)** — verifies compliance with this SOP and the template; final approver.

## 4. Document identification
- ID format `<TYPE>-<SYS>-<NNN>`: TYPE ∈ {URS, FS, DRP, CCR}; SYS ∈ {SUP, NAV, …} per the estate map; NNN sequential.
- Location `docs/gxp/controlled/<system>/<DOC-ID>.md` (system of record = Git, change = PR).
- Versions: `0.x DRAFT` until approved; `1.0` first approved issue; minor bump for editorial, major bump for content.

## 5. Authoring
1. Start from the template in `docs/gxp/baseline/templates/` for the document type; keep every section.
2. Derive content from the **change** (ticket + PR diff + merged code + tests), not from memory or intent.
3. Give every requirement / function / scenario / risk a stable ID and an observable acceptance criterion.
4. Fill the traceability matrix: every requirement maps to source, design, code path, test and change reference.
   Gaps are written as `GAP — <action>`; they are never left blank.
5. Complete *Impact on validated state* and *Revision history*.
6. Use the approved past documents in `docs/gxp/baseline/approved/` as the style reference.
7. Synthetic or anonymised data only; no personal data, credentials or production identifiers.

## 6. Review and approval
1. The author opens a PR titled `UC2 GxP: <DOC-ID> <doc type> for <change>` that changes only `docs/gxp/controlled/**`.
2. The PR body links the ticket and code PR and contains the ticked QA checklist (§8) as the author's self-check.
3. Technical Reviewer, System Owner and QA review in that order; findings are PR comments, classified
   **Critical** (blocks approval), **Major** (must fix before approval) or **Minor** (fix or justify).
4. Approval = PR approval by each named role; QA merges. Merge date = effective date. Part 11 §11.50 meaning is the
   role's "Signature meaning" in the approvals block.

## 7. Periodic review and keeping documents current
Every merge or release to a validated system triggers an impact assessment (SOP-IT-002 §6). Affected controlled
documents are updated in the same release window. Documents are reviewed at least every 24 months.

## 8. QA review checklist (reviewer ticks each item)
| # | Check | Ref |
|---|---|---|
| Q1 | Document ID, version, status, system, GAMP category and GxP impact are present and correct | §4 |
| Q2 | Correct template used; every template section present (or `N/A — reason`) | §5.1 |
| Q3 | Change reference links the ticket **and** the PR / merge commit | §5.2 |
| Q4 | Content matches the code and tests at the referenced commit (spot-check ≥ 3 claims) | §5.2 |
| Q5 | Every requirement / function / scenario / risk has a unique stable ID | §5.3 |
| Q6 | Every requirement is testable (observable acceptance criterion) | §5.3 |
| Q7 | Traceability matrix complete: requirement → source → design → code → test → change; gaps flagged | §5.4 |
| Q8 | Impact on validated state completed, incl. revalidation decision and data-integrity / Part 11 impact | §5.5 |
| Q9 | Revision history entry for this version with change reference | §5.5 |
| Q10 | Approvals block lists Author, System Owner, Technical Reviewer, QA; AI authorship disclosed; not self-approved | §3, §6 |
| Q11 | Synthetic data only; no secrets, PII or production identifiers | §5.7 |
| Q12 | PR changes only `docs/gxp/controlled/**` and is titled per §6.1 | §6.1 |

## 9. Revision history
| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2025-02-03 | QA CSV team | First issue |
| 2.0 | 2026-10-30 | QA CSV team | Added AI-drafted documents (§3, §6), Git as system of record, checklist Q10–Q12 |
