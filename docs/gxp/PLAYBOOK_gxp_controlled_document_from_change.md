# GxP controlled document from change

## Overview
Draft or update **one** GxP controlled document (URS, Functional/Design Specification, DR plan or Change Control
Record) for **one** change (Jira ticket, merged PR or release) in a validated system, and open it as a docs-only PR
for QA review and sign-off. Devin is the author under governance (this playbook, SOP-QA-001, ACU caps); humans
review and approve. Synthetic data only.

## What's Needed From User
- Repository (default `amitmanchella-cog/gsk-scale-ai-demo`) and **baseline ref** if the baseline is not yet on
  `main` (e.g. a branch name). Baseline = `docs/gxp/baseline/` + `docs/gxp/ESTATE_MAP.md`.
- **Change**: ticket key/URL and PR number(s) or release tag.
- **System** folder name and SYS code from the estate map (e.g. `navigator`/`NAV`, `supply_api`/`SUP`).
- **Document type** (URS | FS | DRP | CCR) and **DOC-ID** (e.g. `URS-NAV-001`). If omitted, take the next free number
  from ESTATE_MAP §5; if a document with that ID already exists, update it and bump the version.

## Procedure
1. Branch from `main` as `devin/<unix-ts>-uc2-gxp-<doc-id-lowercase>`. If the baseline is not on `main`, read it from
   the baseline ref with `git fetch origin <ref>` and `git show origin/<ref>:<path>` — do not merge or copy baseline
   files into your branch.
2. Read the baseline: the template for the document type (`templates/<TYPE>_TEMPLATE.md` + `_COMMON_HEADER.md`),
   SOP-QA-001 (incl. QA checklist Q1–Q12), SOP-IT-002 (§6 matrix, checklist C1–C7), the approved reference document of
   the same type in `approved/`, and `ESTATE_MAP.md` for system code, GAMP category and GxP impact.
3. Read the change: ticket (Jira REST/MCP), PR description, `gh pr diff <n>`, merge commit, CI checks. Read the code
   and tests at the merge commit — the document describes the code **as built**, not the intent.
4. Read requirements sources for the system (e.g. `docs/uc4/PRD.md`). Requirements that are in the source but not yet
   implemented at the commit are listed with status `Not implemented in this change` and a `GAP —` note.
5. Write `docs/gxp/controlled/<system>/<DOC-ID>.md` from the template: keep every section and the common header,
   approvals block (Author = "Devin (AI-drafted, playbook GxP controlled document from change)", other roles blank),
   version `0.1 DRAFT` (or bump), stable IDs for every requirement/function/scenario/risk.
6. Fill the traceability matrix: every requirement row maps to source → design ref → code path(s) → test(s) (file::name)
   → ticket + PR. Verify every path and test name exists (`ls`, `grep -n "def test_"`). No blank cells.
7. Complete *Impact on validated state* and *Revision history* (with ticket + PR).
8. Self-check: run the QA checklist Q1–Q12 (and C1–C7 for a CCR) against the document; fix anything failing.
   `git diff --name-only origin/main` must list only `docs/gxp/controlled/**`.
9. Open a PR into `main` titled `UC2 GxP: <DOC-ID> <doc type> for <change>`. Body: summary, links to ticket and PR,
   the filled Q1–Q12 checklist as `- [x]` / `- [ ]` with one-line evidence each, open gaps, and "Synthetic data only.
   Requires Technical Reviewer, System Owner and QA approval (SOP-QA-001 §6). Do not merge without QA."
10. Comment the PR link on the ticket (if Jira is reachable) and report the PR URL.

## Specifications
- Exactly one document, one PR, docs-only (`docs/gxp/controlled/**`). CI stays green.
- Every requirement traces to code path, test and ticket/PR; gaps are explicit, never blank.
- PR body contains the ticked SOP-QA-001 checklist.
- No real GSK data, names, credentials or production identifiers.

## Advice and Pointers
- Doc types: URS = what users need (testable acceptance criteria) · FS = how the code does it (endpoints, modules,
  config) · DRP = RTO/RPO, scenarios, executable restore steps, post-restore tests · CCR = change summary, scope from
  the diff, ICH Q9 risk table, CI evidence, back-out plan, linked documents.
- Sibling documents for the same change are drafted in parallel by other sessions; reference them by DOC-ID
  (URS ↔ FS ↔ DRP ↔ CCR) but do not create them.

## Forbidden Actions
- Do not modify application code, tests, CI, notebooks, or the baseline.
- Do not merge, close or edit other PRs; do not edit tickets other than adding a comment on the change ticket.
- Do not approve or sign the document yourself.
