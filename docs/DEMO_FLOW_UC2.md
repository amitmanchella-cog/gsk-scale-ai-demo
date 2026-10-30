# UC2 demo flow — "Prove it": GxP controlled documents drafted from every change

**Length:** 8 minutes · **Audience:** GSK QA / CSV (computerised system validation) leads, R&D IT system owners,
agentic-factory owners · **Story position:** UC1 *build the data* → UC4 *build the product* → **UC2 *prove it*** → UC3 *run it*

**Story recap (3 lines).** Validated systems need controlled documents — URS, design specs, DR plans, change-control
records — for every change. Today engineers, product and QA write them by hand: **a single URS takes 35–40 hours**, and
documents drift from the code. In UC2 Devin maps the validated estate, reads the baseline (templates, SOPs, approved
past documents), and on each change drafts **one controlled document per session, in parallel**, as a docs-only PR that
QA reviews and signs off — traceable to the ticket and PR. An Automation keeps it running on every merge. Devin is
managed infrastructure and governance (playbooks, Automations, ACU caps) that complements GSK's agentic factory.
**Synthetic data only** — the validated systems are this repo's `services/supply_api` and `apps/navigator`.

## Pre-demo checklist (do this the day before)

1. Open the estate map and baseline on the parent PR https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/21 (or `main` if merged) and skim
   [`docs/gxp/ESTATE_MAP.md`](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/1793368744-uc2-gxp-baseline/docs/gxp/ESTATE_MAP.md).
2. Open DeepWiki https://deepwiki.com/amitmanchella-cog/gsk-scale-ai-demo and confirm it renders the repo
   and the Devin Wiki https://devin-gtm.devinenterprise.com/wiki/amitmanchella-cog/gsk-scale-ai-demo (generated for this demo on 2026-10-30). Present the Devin Wiki; public DeepWiki
   returned a bot checkpoint (HTTP 429) during the build. If neither loads, show the estate map (tab 3).
3. Confirm the four fleet PRs are open and green (tab table) and that the QA review comment is on https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18 (URS-NAV-001, QA comment https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18#issuecomment-6524740512).
4. Confirm the playbook page (org playbook pending approval card — versioned source `docs/gxp/PLAYBOOK_gxp_controlled_document_from_change.md`) loads and the Automation (Automation created disabled, pending approval card — prompt `docs/gxp/automation/devin_automation_prompt.md`) shows **Disabled** (it is
   shown, not fired, in the demo).
5. Optional live beat: in the Devin webapp, start one extra session with the playbook (tab 5), prompt "DOC-ID FS-SUP-001,
   type FS, system supply_api/SUP, change PR #1" (fills the FS gap in ESTATE_MAP §4). Not required — the four
   recorded sessions carry the beat.
6. Check Jira [MBA-3680](https://cog-gtm.atlassian.net/browse/MBA-3680) shows the four PR links in comments.
   **Do not touch MBA-3651 or PR #14** — they belong to the UC4 live beat.

### Tabs to pre-open (left to right)

| # | Tab | URL |
|---|---|---|
| 1 | Change ticket MBA-3680 (Navigator v0.1, synthetic) | https://cog-gtm.atlassian.net/browse/MBA-3680 |
| 2 | Devin Wiki — the validated estate (generated for this demo) | https://devin-gtm.devinenterprise.com/wiki/amitmanchella-cog/gsk-scale-ai-demo |
| 2b | Public DeepWiki (same repo; may show a checkpoint) | https://deepwiki.com/amitmanchella-cog/gsk-scale-ai-demo |
| 3 | Estate map | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/1793368744-uc2-gxp-baseline/docs/gxp/ESTATE_MAP.md |
| 4 | Baseline (templates, SOPs, approved docs) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/tree/devin/1793368744-uc2-gxp-baseline/docs/gxp/baseline |
| 5 | Playbook "GxP controlled document from change" | (org playbook pending approval card — versioned source `docs/gxp/PLAYBOOK_gxp_controlled_document_from_change.md`) |
| 6 | Fleet session — URS-NAV-001 | https://devin-gtm.devinenterprise.com/sessions/9b6d5495414a46569c148547fe272f38 |
| 7 | Fleet session — FS-NAV-001 | https://devin-gtm.devinenterprise.com/sessions/1e49508fe65c4e55929ae31a351591c3 |
| 8 | Fleet session — DRP-NAV-001 | https://devin-gtm.devinenterprise.com/sessions/0d79cc7b00ed4b6d8b27d96e6ee16bf3 |
| 9 | Fleet session — CCR-NAV-001 | https://devin-gtm.devinenterprise.com/sessions/dbf21b4a44154051a6d06e3a3071769a |
| 10 | Fleet PRs (URS · FS · DRP · CCR) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/17 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/20 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/19 |
| 11 | QA-reviewed PR (the one you open) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18 (URS-NAV-001, QA comment https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18#issuecomment-6524740512) |
| 12 | Automation (disabled draft) | (Automation created disabled, pending approval card — prompt `docs/gxp/automation/devin_automation_prompt.md`) |
| 13 | The change itself: PR #8 Navigator scaffold | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8 |

## Main flow (8 minutes)

| Time | Tab | Action | Say | Note |
|---|---|---|---|---|
| 0:00 | 1 — MBA-3680 | Show the ticket | "Every change to a validated system needs controlled documents — URS, design spec, DR plan, change-control record. Today people write them by hand: **a single URS is 35–40 hours**, and the documents drift from the code the day after sign-off." | **Step 1 — frame the problem.** Synthetic ticket: Navigator v0.1 entering the validated estate via PR #8. |
| 1:00 | 2 — Devin Wiki | Scroll the repo overview / architecture | "First Devin maps the estate: DeepWiki has indexed the repo — the two validated systems, their components, endpoints and tests." | **Step 2 — map the estate.** Fallback: Devin Wiki page or tab 3. |
| 1:30 | 3 — ESTATE_MAP.md | Scroll to §4 *exist vs missing* | "This is the map Devin wrote: supply_api has an approved URS, DR plan and CCR; the Navigator has a PRD and **no controlled documents at all**. That's the gap this change must close." | §6 is the change→document matrix the Automation uses. |
| 2:15 | 4 — baseline | Open `templates/URS_TEMPLATE.md`, then `sop/SOP-QA-001.md` §8 | "The baseline is yours, not ours: templates with document ID, version, approvals, traceability matrix, impact on validated state and revision history; the SOPs; and approved past documents as the style reference." | **Step 3 — set the baseline.** GAMP 5 / Part 11 / Annex 11 flavour; QA checklist Q1–Q12. |
| 3:00 | 5 — playbook | Scroll the Procedure | "The playbook is the engineering standard as text: one document per session, read the template, SOP, ticket and diff, describe the code *as built*, trace every requirement to code, test and ticket, docs-only PR. Change it once, every team follows." | Versioned copy in `docs/gxp/PLAYBOOK_*.md`. |
| 3:30 | 6–9 — sessions | Flip through the four sessions | "On this change Devin launched a fleet — four sessions in parallel, one per controlled document, each ACU-capped, each with its own PR." | **Step 4 — launch the fleet.** Fast mode. Optional: start a fifth live. |
| 4:15 | 10 — fleet PRs | Show the four PR titles | "Each is a docs-only PR titled by document ID, written to the system of record, linked to the ticket and the code PR." | All changes under `docs/gxp/controlled/navigator/`. |
| 4:45 | 11 — QA PR | Open *Files changed*, scroll header + approvals | "Here's one, as QA sees it: document ID, version 0.1 DRAFT, GAMP category, GxP impact, the change reference — and an approvals block where AI authorship is disclosed and **nobody has signed yet**." | **Step 5 — show the evidence.** |
| 5:30 | 11 — QA PR | Scroll to the traceability matrix | "Every requirement maps to a source, a code path, a test and the ticket/PR. Requirements in the PRD the scaffold doesn't implement yet are flagged as gaps, not invented." | Spot-check one row: open the code path. |
| 6:00 | 11 — QA PR | Open the PR body checklist, then the QA review comment | "The author's SOP checklist is filled in the PR body; here is the QA review against SOP-QA-001 and the template — findings classified, decision recorded. Approval is the PR review; merge is the effective date." | 21 CFR Part 11 §11.50: name, date, meaning. |
| 6:45 | 12 — Automation | Show trigger, prompt, limits | "To keep documents current, this Automation fires on every merge to main, maps changed files to affected documents and starts one playbook session per document — 10 ACUs per run, 6 runs an hour, network allowlist. It is a disabled draft until QA approves the process." | **Step 6 — keep it running.** Release trigger: GitHub Actions stub in `docs/gxp/automation/`. |
| 7:30 | — | Close | "35–40 hours of drafting becomes a QA review of a traceable draft. GSK's agentic factory decides what to build; Devin is the governed infrastructure that documents and proves it — playbooks, Automations, ACU caps. Synthetic data only." | Hand over to UC3. |

## Fallback box — if something is slow or down

- **DeepWiki** shows a checkpoint / not indexed → open tab 3 (ESTATE_MAP.md): "this is the same map, written by Devin into the repo."
- **A fleet session is still running** → open the finished ones; the PR list (tab 10) is the evidence. Say: "the sessions are independent, one can lag without blocking the others."
- **Jira unreachable** → the ticket key and link are in every PR body and in the document header.
- **Approval card not yet clicked for the Automation** → show `docs/gxp/automation/devin_automation_prompt.md` and the GitHub Actions stub `gxp-controlled-docs.yml.example`.

## Governance close (what to repeat)

- **Playbooks**: one versioned standard for every controlled document; SOP checklist in every PR.
- **Automations**: merge/release → affected documents redrafted; disabled until approved; loop-protected (never fires on `uc2-gxp` doc PRs).
- **ACU caps**: 10 ACUs per run, 6 runs/hour, 2 concurrent; per-child sessions billed and visible.
- **Humans sign**: Devin never approves; Technical Reviewer, System Owner and QA approve in the PR.
- **Synthetic data only**; no real GSK systems, SOPs, people or data.
