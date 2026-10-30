# GSK Scale AI demo — presenter runbook (30 minutes)

**One repo, one story.** UC1 *build the data* → UC4 *build the product* → UC3 *run it*.
Repo: https://github.com/amitmanchella-cog/gsk-scale-ai-demo · All data is synthetic (seeded generator, 1,600 fake HCPs, 30 reps, 20 territories). No real GSK names, data, CRM or PII anywhere.

**The one sentence to land:** *Devin is managed infrastructure and governance for software delivery — playbooks and Automations make the engineering standard the default for every team and SI partner, and it complements GSK's agentic factory rather than competing with it.*

| Segment | Minutes | Flow doc (read it the night before) |
|---|---|---|
| Opening | 0:00–1:00 | this page, section 1 |
| UC1 — build the data (notebook → tested PySpark job) | 1:00–11:00 | [docs/DEMO_FLOW_UC1.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/main/docs/DEMO_FLOW_UC1.md) |
| UC4 — build the product (Jira PRD → gated SDLC → Field Force Navigator) | 11:00–21:00 | [docs/DEMO_FLOW_UC4.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/main/docs/DEMO_FLOW_UC4.md) |
| UC3 — run it (CI failure → self-heal Automation) | 21:00–29:00 | [docs/DEMO_FLOW_UC3.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/main/docs/DEMO_FLOW_UC3.md) |
| Governance wrap-up | 29:00–31:00 | this page, section 5 |

---

## 0. Before the call — do these the day before (15 min)

Things only the repo/Jira admin can do; Devin was blocked (HTTP 403) on each:

- [ ] **Make the repo private**: https://github.com/amitmanchella-cog/gsk-scale-ai-demo/settings → Danger zone → Change visibility.
- [ ] **UC4 release gate**: https://github.com/amitmanchella-cog/gsk-scale-ai-demo/settings/environments → `non-prod` → *Required reviewers* → add yourself. Without it the "Review deployments" click at UC4 minute 8:00 never appears.
- [ ] **UC3 trigger check**: open https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/3, click *Checks* → failed check → *View workflow run* → *Re-run failed jobs*. Within ~2 min a session tagged `uc3-self-heal` must appear at https://devin-gtm.devinenterprise.com/sessions?tags=uc3-self-heal. If it does not, the `github:check_run` webhook is not reaching Devin — raise it with Cognition and plan to use the Automation page's **Run now** on the call (see UC3 fallback).
- [ ] **Paste the two Automation session URLs** (PR A and PR B) into `docs/DEMO_FLOW_UC3.md` where it says `<<SESSION_URL_A>>` / `<<SESSION_URL_B>>` (open a PR on a `devin/*` branch so the Automation ignores it).
- [ ] **Jira live ticket** https://cog-gtm.atlassian.net/browse/MBA-3651: Story, title *Field Force Navigator: Territory Call Planner*, description = `docs/uc4/PRD.md`, status To Do, zero comments. Do not touch it in rehearsals.
- [ ] Delete the inert one-shot reminder automation `auto-30fe1482b16b405caede15fc61220ef6` (Automations page) — housekeeping only.

## 1. Opening (1 min)

| Minute | Say |
|---|---|
| 0:00 | "Three use cases, one repository, one story. A field-force analytics team: first we turn a messy notebook into a production PySpark job, then we build a product on that data from a Jira ticket through a gated SDLC, then we keep it running when CI breaks — all with Devin acting as governed, managed engineering infrastructure. Everything you will see is synthetic data." |
| 0:40 | "Watch for three things throughout: the standard lives in a **playbook**, the trigger lives in an **Automation**, and a **human approves** every gate — Devin never approves Devin." |

## 2. UC1 — build the data (10 min) → `docs/DEMO_FLOW_UC1.md`

Tabs to pre-open: messy notebook · merged PR #2 (Files changed) · green CI run 41011065616 · `jobs/territory_kpis.json` · playbook **Notebook to PySpark job** · pre-run session A · second notebook `hcp_engagement.ipynb`.

| Minute | Beat | Key click | One line to say |
|---|---|---|---|
| 0:00 | The messy notebook | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/main/notebooks/territory_kpis.ipynb | "pandas and PySpark in one notebook, hard-coded paths, `toPandas()` mid-pipeline — it will never scale." |
| 1:30 | What Devin shipped | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/2/files | "Extract / transform / quality / load, 39 tests, DQ gates, parity check, Databricks job JSON — shown, not run; no Databricks account needed." |
| 3:10 | Proof | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011065616 | "CI says `520 rows compared, 0 mismatches` — GitHub Actions on local Spark, not Devin's claim." |
| 4:00 | **LIVE** | Playbook page https://devin-gtm.devinenterprise.com/settings/playbooks/9e1fef4a89a84b19901df5f30c3078e6 → new session on the repo → paste prompt below | "One prompt, four facts; the engineering standard comes from the playbook." |
| 7:00 | While it runs | Pre-run session https://devin-gtm.devinenterprise.com/sessions/91a1d13228e543a88dd2c86a8dc7ace4 | "Parity caught pandas half-even vs Spark half-up rounding — 30 cells — and Devin fixed it. That is why the gate exists." |
| 9:00 | Close | Playbook + CI tabs | "Change the playbook once, every future conversion follows. Three CI gates, no credentials." |

Prompt to paste (verbatim):

```
Convert notebooks/hcp_engagement.ipynb into pipelines/hcp_engagement/ following the playbook; parity key hcp_id; expected output notebooks/expected_output/hcp_engagement.parquet
```

Fallback: after 30 s of nothing, switch to session A and PR #2; come back at 9:00. Never merge a rehearsal PR that creates `pipelines/hcp_engagement/` — the live run needs it absent.

## 3. UC4 — build the product (10 min) → `docs/DEMO_FLOW_UC4.md`

Tabs: Jira MBA-3651 · new Devin session · fallback session https://devin-gtm.devinenterprise.com/sessions/df5a35cb1f09422ea4363ec7efc72af7 · fallback PR #14 · artefacts on branch `devin/MBA-3650` (requirements.md, design.md, test-report.md) · Jira MBA-3650 · deploy run 41026121962.

| Minute | Beat | Key click | One line to say / do |
|---|---|---|---|
| 0:00 | Ticket = PRD | https://cog-gtm.atlassian.net/browse/MBA-3651 | "The only input: one Story — users, three features, six acceptance criteria, named approvers per phase." |
| 1:00 | **LIVE** start | New Devin session, paste Prompt B (below) | "Run the whole SDLC against the ticket; stop at every gate for a human." |
| 2:00 | Requirements gate (live, ~4 min in) | Live session | You are the Product Owner: read `requirements.md` + sub-tasks, type `APPROVED`. |
| 3:30 | Switch to pre-run | Fallback session + PR #14 | "Build alone takes ~55 min, so here is the identical prompt run earlier today on a twin ticket." |
| 3:30 | Design gate | `design.md` on `devin/MBA-3650` | Tech Lead: mermaid architecture, API contract, scoring example (A + 45 days + open follow-up = 100). |
| 5:00 | Build | PR #14 → Checks | "Five child sessions, one per story, three CI jobs green: lint+tests (100 % scoring coverage), frontend, container." |
| 6:30 | Verify gate | `test-report.md` + recording | QA: AC1–AC6 all pass, recorded in a 2 min 23 s browser run. |
| 8:00 | Release gate | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41026121962 | Release Manager: `non-prod` environment with required reviewer; image pushed to GHCR; "no cloud target, and Devin said so." |
| 8:40 | Ticket closes | https://cog-gtm.atlassian.net/browse/MBA-3650 | "Done, five sub-tasks Done, one comment per gate — 80 min prompt-to-Done." |
| 9:50 | Back to live | Live session | Show where it has got to; hand off to UC3. |

Prompt B to paste (verbatim):

```
Run the full SDLC for Jira ticket MBA-3651 in repo amitmanchella-cog/gsk-scale-ai-demo, under apps/navigator/. Read the ticket with the Jira MCP; it is the PRD. Data comes from the UC1 curated tables in pipelines/territory_kpis.
At the end of phases 1, 2 and 4, post the artefact as a Jira comment and STOP until I reply "APPROVED". Any other reply is a change request.
1 Requirements: docs/uc4/requirements.md + one Jira sub-task per story.
2 Design: docs/uc4/design.md (mermaid architecture, data model, API contract, scoring worked example, test plan).
3 Build: branch devin/MBA-3651, one child session per story, unit + component tests, Dockerfile, CI green, one PR linking the ticket and docs.
4 Verify: run the app, test every acceptance criterion, record it, docs/uc4/test-report.md.
5 Release: deploy job to GitHub Environment "non-prod" with a required reviewer (build and push the image if there is no cloud target, and say so). Final Jira comment with all links, then move the ticket to Done.
```

Rules: never approve a phase yourself — you *play* the approvers. Do not merge PR #14 or the live PR on stage. `main` must stay at the clean scaffold `20e748e3`.

## 4. UC3 — run it (8 min) → `docs/DEMO_FLOW_UC3.md`

Tabs: Automation https://devin-gtm.devinenterprise.com/automations/b09f21a5803c4fb69d049070a961ef94 · PR #3 (A) + its session · PR #4 (B) + its session · PR #5 (C, red, untouched) · sessions filtered by tag `uc3-self-heal` · Actions page.

| Minute | Beat | Key click | One line to say |
|---|---|---|---|
| 0:00 | The Automation | Automation page | "Fires only on a failed check run, only in this repo, never on `main` or `devin/*` branches (loop protection); 10 ACUs per run, 6 runs/hour, 3 concurrent; six allowed hosts; the prompt is the standard: reproduce → regression test that fails first → smallest fix → push to the PR branch → one root-cause comment; never skip or weaken a test." |
| 1:30 | PR A — timezone bug | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/3 + its session | "A report ending 23:30 New York was filed under the UTC date — wrong day, wrong week for a Tokyo site. Devin wrote the failing test first, then fixed `to_site_local_date()`." |
| 3:30 | PR B — broken import | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/4 | "Rename updated the caller, not the tests; whole module failed to import. Same guardrails, author's intent kept." |
| 4:30 | **LIVE** PR C | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/5 → Checks → failed check → View workflow run → Re-run failed jobs | "I'm re-emitting the failure event, exactly what a push would do." Then refresh the `uc3-self-heal` sessions list. |
| 5:45 | Narrate | New session | "Reading the log, reproducing `test_product_default_lead_time_is_six_weeks`, regression test, smallest fix — or it stops and asks because the test and the change disagree on intent. Either is the right behaviour." |
| 6:30 | Close | Automation page | "A budget, not a blank cheque; one repo, six hosts, never `main`; PR comment + transcript as audit trail; usage rolls up by tag." |

Fallbacks: no session 90 s after the re-run goes red → open the PR A/B sessions and comments, say "trigger latency is webhook delivery, the Automation is queued". If the webhook is known-dead (see section 0), use **Run now** on the Automation page with PR C's run as the event — same prompt, same limits. Mention: the same Automation can be fired from an **Azure Monitor** alert via an action-group webhook to the Devin API.

## 4b. UC2 — prove it (8 min, optional segment) → `docs/DEMO_FLOW_UC2.md`

Use when the audience includes QA / CSV owners; slot it between UC4 and UC3 (the 30-minute run becomes 38). Synthetic data only.

Tabs: MBA-3680 https://cog-gtm.atlassian.net/browse/MBA-3680 · Devin Wiki https://devin-gtm.devinenterprise.com/wiki/amitmanchella-cog/gsk-scale-ai-demo (DeepWiki https://deepwiki.com/amitmanchella-cog/gsk-scale-ai-demo) · `docs/gxp/ESTATE_MAP.md` · `docs/gxp/baseline/` · playbook (org playbook pending approval card — versioned source `docs/gxp/PLAYBOOK_gxp_controlled_document_from_change.md`) · four fleet sessions + PRs (URS/FS/DRP/CCR-NAV-001) · QA-reviewed PR https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18 (URS-NAV-001, QA comment https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18#issuecomment-6524740512) · Automation (Automation created disabled, pending approval card — prompt `docs/gxp/automation/devin_automation_prompt.md`) (disabled draft).

| Minute | Beat | Key click | One line to say |
|---|---|---|---|
| 0:00 | Frame | MBA-3680 | "Every change to a validated system needs URS, design spec, DR plan, change-control record — **a URS takes 35–40 hours by hand**, and documents drift from the code." |
| 1:00 | Map the estate | DeepWiki → ESTATE_MAP §4 | "Two validated systems; supply_api is documented, the Navigator has a PRD and no controlled documents." |
| 2:15 | Baseline | URS template → SOP-QA-001 §8 | "Your templates, your SOPs, your approved past documents — Devin follows them, it doesn't invent a format." |
| 3:00 | Playbook | Playbook page | "One document per session, described as built, every requirement traced to code, test, ticket and PR." |
| 3:30 | Fleet | Four sessions, four PRs | "Four sessions in parallel, one per controlled document, each ACU-capped, each a docs-only PR." |
| 4:45 | Evidence | QA PR → header, traceability, checklist, QA comment | "QA reviews a traceable draft against the SOP; AI authorship disclosed, nobody signs but humans." |
| 6:45 | Keep it running | Automation page | "Every merge to main → affected documents redrafted; 10 ACUs/run, 6 runs/hour; disabled until QA approves." |
| 7:30 | Close | — | "35–40 hours of drafting becomes a review. Devin is the governed infrastructure that complements GSK's agentic factory." |

Fallbacks: DeepWiki checkpoint → ESTATE_MAP.md · a session still running → show the finished PRs · Automation not approved → `docs/gxp/automation/` prompt + GitHub Actions stub.

## 5. Governance wrap-up (2 min)

| Minute | Say | Show |
|---|---|---|
| 0:00 | "**Guardrails** — every Automation and session ran inside a sandbox with a network allowlist, repo scope, `devin/*` branches, never `main`, never a skipped test, never a self-approved gate." | Automation page: trigger, allowlist, prompt |
| 0:30 | "**ACU caps** — 10 ACUs per self-heal run, 6 runs an hour, per-story child sessions with their own caps: the cost ceiling is known before the work starts." | Automation limits |
| 1:00 | "**Playbooks** — the notebook standard and Prompt B are versioned text any team or SI partner starts from; change it once, everyone follows." | https://devin-gtm.devinenterprise.com/settings/playbooks/9e1fef4a89a84b19901df5f30c3078e6 |
| 1:30 | "**Analytics** — sessions are tagged (`gsk-demo`, `uc3-self-heal`), so usage, ACUs and outcomes roll up per tag, team or repo for platform owners." | Devin usage/analytics page, filter by tag |
| 1:50 | "GSK's agentic factory decides what to build; Devin is the governed engineering infrastructure that builds, verifies and keeps it running. Complements, doesn't compete." | — |

## 6. Everything built for this demo (reference)

| Item | Link |
|---|---|
| Repo | https://github.com/amitmanchella-cog/gsk-scale-ai-demo |
| UC1 parent session / children | https://devin-gtm.devinenterprise.com/sessions/6040eb136e7145d19ee3cf3ab0f389a9 · A https://devin-gtm.devinenterprise.com/sessions/91a1d13228e543a88dd2c86a8dc7ace4 · B https://devin-gtm.devinenterprise.com/sessions/dd32829c17af4dc9a4383e85248a2632 |
| UC1 PRs | #2 pipeline https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/2 · #6 doc https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/6 |
| Playbook | https://devin-gtm.devinenterprise.com/settings/playbooks/9e1fef4a89a84b19901df5f30c3078e6 |
| UC4 parent session | https://devin-gtm.devinenterprise.com/sessions/11d9cb012bc14a3b913a3e020b677910 |
| UC4 fallback SDLC session / PR | https://devin-gtm.devinenterprise.com/sessions/df5a35cb1f09422ea4363ec7efc72af7 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/14 (open, do not merge) |
| UC4 PRs | #8 scaffold · #9–#13 stories (into `devin/MBA-3650`) · #15 doc |
| Jira | MBA-3650 (fallback, Done) https://cog-gtm.atlassian.net/browse/MBA-3650 · MBA-3651 (live) https://cog-gtm.atlassian.net/browse/MBA-3651 |
| UC3 parent session / children | https://devin-gtm.devinenterprise.com/sessions/e266d23a031b4bdbbd26fdd99bb374e2 · API https://devin-gtm.devinenterprise.com/sessions/8e83faaab6354ed48b8377836dd0acf4 · doc https://devin-gtm.devinenterprise.com/sessions/62b285af85374f2aba11f2816c265f0f |
| UC3 PRs | #1 supply_api · #3 A · #4 B · #5 C (keep red) · #7 doc |
| Automation | https://devin-gtm.devinenterprise.com/automations/b09f21a5803c4fb69d049070a961ef94 |
| UC2 parent session / fleet | https://devin-gtm.devinenterprise.com/sessions/14340a70d82941c791bb3f0aebb05ad2 · URS https://devin-gtm.devinenterprise.com/sessions/9b6d5495414a46569c148547fe272f38 · FS https://devin-gtm.devinenterprise.com/sessions/1e49508fe65c4e55929ae31a351591c3 · DRP https://devin-gtm.devinenterprise.com/sessions/0d79cc7b00ed4b6d8b27d96e6ee16bf3 · CCR https://devin-gtm.devinenterprise.com/sessions/dbf21b4a44154051a6d06e3a3071769a |
| UC2 PRs / playbook / Automation | parent <<PR_PARENT>> · fleet https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/18 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/17 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/20 · https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/19 · playbook (org playbook pending approval card — versioned source `docs/gxp/PLAYBOOK_gxp_controlled_document_from_change.md`) · Automation (Automation created disabled, pending approval card — prompt `docs/gxp/automation/devin_automation_prompt.md`) · Jira MBA-3680 |
| Orchestrating session | https://devin-gtm.devinenterprise.com/sessions/0f8f8aee7bf3446baaadce42f0a9f093 |
