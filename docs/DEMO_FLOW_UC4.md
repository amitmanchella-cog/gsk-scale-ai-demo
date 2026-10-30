# UC4 demo flow — "Build the product": Jira PRD → phase-gated SDLC → Field Force Navigator

**Length:** 10 minutes · **Audience:** GSK engineering / product / platform leads, SI partners, agentic-factory owners
· **Story position:** UC1 *build the data* → UC4 *build the product* → UC3 *run it*

**Premise.** A Product Owner files one Jira Story — the PRD for the **Field Force Navigator: Territory Call Planner**.
One prompt asks Devin to run the whole SDLC against it: requirements → design → build → verify → release, stopping at
each phase gate until a named GSK approver replies `APPROVED`. The output is a working app in `apps/navigator/`
(FastAPI + React) on top of the UC1 curated tables, a PR with green CI, a recorded test report, a gated deploy job and
an auditable Jira trail. Everything shown is synthetic data; no real HCP names or PII.

**One repo, one story.** UC1 built the data (`pipelines/territory_kpis`, playbook) → **UC4 builds the product from
that data (this demo)** → UC3 runs it (CI self-heal Automation).

## Before the call (10 minutes before)

Pre-open these tabs, left to right, in this order:

| # | Tab | URL |
|---|---|---|
| 1 | Jira — **live** ticket MBA-3651 (the PRD) | https://cog-gtm.atlassian.net/browse/MBA-3651 |
| 2 | Devin — new session (Prompt B goes here at 1:00) | https://devin-gtm.devinenterprise.com |
| 3 | **Fallback pre-run session** (same prompt, run earlier today on MBA-3650) | https://devin-gtm.devinenterprise.com/sessions/df5a35cb1f09422ea4363ec7efc72af7 |
| 4 | Fallback PR #14 (label `uc4-fallback`, **do not merge**) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/14 |
| 5 | Fallback artefacts on branch `devin/MBA-3650` | [requirements.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/requirements.md) · [design.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/design.md) · [test-report.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/test-report.md) |
| 6 | Jira — fallback ticket MBA-3650 (Done, sub-tasks MBA-3659..MBA-3663, final comment with all links) | https://cog-gtm.atlassian.net/browse/MBA-3650 |
| 7 | GitHub Actions — green *Deploy navigator (non-prod)* run | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41026121962 |
| 8 | GitHub Actions — all runs (where the live 'Review deployments' click will appear) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions |
| 9 | PRD source file on `main` | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/main/docs/uc4/PRD.md |

Checklist:

- [ ] Tab 1: **MBA-3651** exists in project **MBA**, type **Story**, title *Field Force Navigator: Territory Call Planner*, description = `docs/uc4/PRD.md` verbatim (tab 9), status **To Do**, **no comments**, no sub-tasks. Never touch it in rehearsals — it is the live ticket.
- [ ] `main` is at the clean scaffold commit `20e748e39c98d163c6d1f6fc2398254b3916d3f4` (scaffold PR https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/8): `apps/navigator` has only `/health`, `/reps`, `/territories` and a placeholder page. If a rehearsal merged anything else into `main`, the live run has nothing to build.
- [ ] Tab 3 scrolls and tab 4 is still **Open** (3 CI jobs green). You know where the five phase gates are in the transcript.
- [ ] Tab 7 shows a green run of workflow *Deploy navigator (non-prod)*, job *Push to GHCR (non-prod)*.
- [ ] **Required reviewer on the `non-prod` GitHub Environment is set.** GitHub auto-created the environment on the first run with **no protection rules** — Devin's GitHub App token cannot create environments or set required reviewers (HTTP 403). The repo admin must add themselves as *Required reviewer* at https://github.com/amitmanchella-cog/gsk-scale-ai-demo/settings/environments → `non-prod` **before** the call; only then does the 8:00 *Review deployments* approve click appear in GitHub Actions. If it is not set, the deploy job runs ungated — say so honestly.
- [ ] Signed in to https://devin-gtm.devinenterprise.com, Jira MCP connected (the new-session page shows Atlassian under integrations).
- [ ] Prompt B (below) is in your clipboard with `MBA-3651` in it.
- [ ] Say "synthetic data" at least once; never describe the HCPs as real people.

## Main flow (10 minutes)

| Minute | Step | Where | You play |
|---|---|---|---|
| **0:00** | Jira ticket MBA-3651 = the PRD | Tab 1 | Product Owner |
| **1:00** | Paste Prompt B into a new Devin session | Tab 2 | — |
| **2:00** | Requirements gate → `APPROVED` | Live session (or tab 5 requirements.md) | Product Owner |
| **3:30** | Design gate → `APPROVED` | Tab 3 / tab 5 design.md | Tech Lead |
| **5:00** | Build: child sessions S1–S5, PR, CI green | Tab 3 / tab 4 | Tech Lead (code review) |
| **6:30** | Verify gate: test report + recording → `APPROVED` | Tab 5 test-report.md | QA |
| **8:00** | Release: gated deploy, GHCR image, ticket Done | Tab 7 / tab 6 | Release Manager |
| **9:00** | Governance close | Tab 3 + tab 6 | — |

### 0:00 — The ticket is the PRD (1 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 0:00 | Tab 1 — https://cog-gtm.atlassian.net/browse/MBA-3651 | "This is the only input: a Jira Story written by the Product Owner — problem, users, three features, six acceptance criteria, non-functionals, and who approves each phase." | Project **MBA**, type **Story**, status **To Do**, zero comments. |
| 0:20 | Scroll to *Acceptance criteria* | "AC2 is the scoring rule we will check later: Segment A, 45 days, one open follow-up → 40 + 40 capped + 20 = 100. AC3: visited 3 days ago → 0." | The scoring rules are configurable (A=40, B=25, C=10; +1/day max 40; +20 open follow-up; 0 if visited in 7 days). |
| 0:40 | Scroll to *Phase artefacts and approvers* | "Five phases, five artefacts, four human approvers. Devin stops at each gate until a named person says APPROVED." | Requirements → PO · Design → TL · Build → TL review · Verify → QA · Release → Release Manager. Data = UC1 curated tables, synthetic only. |

### 1:00 — LIVE: one prompt, the whole SDLC (1 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 1:00 | Tab 2 — https://devin-gtm.devinenterprise.com → **New session**, repo `amitmanchella-cog/gsk-scale-ai-demo`, paste Prompt B, start | "One prompt. It names the ticket, the repo folder, the data, the five phases and the gates — and it says *stop until I reply APPROVED*." | The prompt is the engineering standard: artefact per phase, child session per story, coverage gate, CI, gated deploy, `devin/*` branches. |
| 1:30 | Watch the first steps | "It reads the ticket through the Jira MCP, reads the scaffold on `main`, and plans phase 1." | It reads the PRD from Jira, not from a file; `main` is the bare scaffold (`/health`, `/reps`, `/territories`). |

**Prompt B — paste verbatim:**

```
Run the full SDLC for Jira ticket MBA-3651 in repo amitmanchella-cog/gsk-scale-ai-demo, under apps/navigator/. Read the ticket with the Jira MCP; it is the PRD (if Jira is unavailable, use docs/uc4/PRD.md and write each 'Jira comment' to docs/uc4/jira-comments/<phase>.md). Data comes from the UC1 curated tables in pipelines/territory_kpis (and data/*.parquet).
At the end of phases 1, 2 and 4, post the artefact as a Jira comment and STOP until I reply "APPROVED". Any other reply is a change request.
1 Requirements: docs/uc4/requirements.md (stories, Given/When/Then acceptance criteria, traceability to tests) + one Jira sub-task per story.
2 Design: docs/uc4/design.md (mermaid architecture, data model, API contract, scoring worked example, test plan).
3 Build: branch devin/MBA-3651, use one child session per story, unit + component tests (scoring logic >= 90% coverage), Dockerfile, CI green, one PR linking the ticket and docs.
4 Verify: run the app, test every acceptance criterion AC1-AC6, record it, docs/uc4/test-report.md.
5 Release: deploy job to a GitHub Environment "non-prod" with a required reviewer (build and push the image to GHCR if there is no cloud target, and say so). Final Jira comment with all links, then move the ticket to Done.
Branch names must all start with devin/.
```

### 2:00 — Requirements gate: you are the Product Owner (1.5 min)

In the fallback run this gate arrived **4 min 07 s** after the prompt. Narrate the plan until it does; if it has not
arrived by ~3:30, use the **Hybrid approach** below and approve it live when it lands.

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 2:00 | Live session — Devin's phase-1 message, or tab 1 refreshed (the artefact is also a Jira comment) | "Phase 1 done: the PRD became five user stories with Given/When/Then criteria and a traceability matrix to the tests it will write." | S1 HCP list (AC1) · S2 score (AC2, AC3) · S3 plan builder (AC4, AC5) · S4 CSV export (AC6) · S5 packaging, CI gates, NFRs. |
| 2:30 | Click the `docs/uc4/requirements.md` link (fallback copy: https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/requirements.md) | "Notice it measured the data before writing requirements — 30 reps, 20 territories, 1,600 HCPs, 155 never visited — and made the as-of date explicit so the demo isn't 'everyone is a year overdue'." | §3 *Data and definitions*, §6 *Traceability matrix*, §8 *Assumptions and open questions*. |
| 2:50 | Tab 1 — refresh, scroll to sub-tasks (fallback: MBA-3659..MBA-3663 under https://cog-gtm.atlassian.net/browse/MBA-3650) | "One Jira sub-task per story, so every piece of work has one owner, one ticket and one build session." | Five sub-tasks, created by the bot, linked to the Story. |
| 3:10 | Live session — type exactly `APPROVED`, send | "I'm the Product Owner. I read it, I approve it. Anything else I typed would be treated as a change request." | Devin resumes only after the exact word. |

### 3:30 — Design gate: you are the Tech Lead (1.5 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 3:30 | Tab 5 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/design.md → §2 *Architecture* | "Phase 2 is a design a Tech Lead can review in five minutes: a mermaid architecture, data model, API contract, scoring design and test plan." | Mermaid renders on GitHub: React SPA → `app.server:app` (SPA at `/`, API at `/api`) → FastAPI routers → `scoring.py`, `plans.py`, `data.py` → `data/*.parquet`. |
| 3:55 | Same page → §4 *API contract* | "Every endpoint, query, response and error code before a line of code: `GET /reps/{id}/hcps`, `POST /reps/{id}/plan/visits` → 409 when the day is full, `GET …/plan/export.csv`." | The 409 for a 7th visit **is** AC4; the CSV endpoint **is** AC6. |
| 4:15 | Same page → §5 *Scoring design and worked examples* | "And the worked example straight from the acceptance criteria: AC2 = 40 + 40 capped + 20 = 100 with a plain-language reason; AC3 = visited 3 days ago = 0." | Table row **AC2 → 100**, `Segment A (+40), 45 days since last visit (+40, capped), 1 open follow-up (+20)`; **AC3 → 0**, `Visited 3 days ago (within 7 days)`; plus boundary cases (7 vs 8 days) and a custom-rules case. |
| 4:40 | Tab 3 — the phase-2 gate in the fallback transcript (or the live session if it is there) → `APPROVED` | "Tech Lead approves. In the pre-run this gate took 3 minutes 19 seconds, including my read time." | The approval is a human message in the session **and** a Jira comment — two audit trails. |

### 5:00 — Build: child sessions per story, one PR, CI green (1.5 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 5:00 | Tab 3 — https://devin-gtm.devinenterprise.com/sessions/df5a35cb1f09422ea4363ec7efc72af7 → phase-3 section | "Phase 3: the parent session spawns one child session per story and sequences them by dependency — S2 scoring first, then S1 list and S3 planner in parallel, then S4 export and S5 packaging in parallel." | Five child sessions, each on `devin/MBA-3650-s<N>`, each opening a PR **into** `devin/MBA-3650` (PRs #9–#13), not into `main`. |
| 5:30 | Tab 4 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/14 → *Checks* | "The parent merges the five story PRs and opens one PR to `main` linking the ticket and the docs. Three CI jobs must be green." | **Python lint + tests** (`ruff`, `pytest`, 84 backend tests, scoring-coverage gate ≥ 90 % — actual 100 %) · **Navigator frontend** (lint, 23 Vitest tests, build) · **Navigator container** (build + smoke on `/health`, `/api/reps`, `/`). |
| 6:00 | Tab 4 → *Files changed* | "Backend, frontend, tests, Dockerfile, CI workflow, docs — one reviewable change set, and a human still has to review and merge it. Devin does not merge." | `apps/navigator/backend/app/{scoring,views,plans,data,server}.py`, `apps/navigator/frontend/src/…`, `apps/navigator/Dockerfile`, `.github/workflows/ci.yml`. Build phase took **54 min 35 s** in the pre-run. |

### 6:30 — Verify gate: you are QA (1.5 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 6:30 | Tab 5 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/test-report.md | "Phase 4: Devin runs the app and tests every acceptance criterion through the browser — AC1 to AC6 — in one recorded run, and writes the test report QA signs off." | §2 *Results*: six rows, all **Pass**, each with the observed values, a timestamp into the recording and a screenshot. |
| 6:55 | Same page → AC2 and AC3 rows | "Real data: Dr Isla Xu — Segment A, 51 days, one open follow-up — scores 100 with the reason spelled out; Dr Finn Young visited 3 days ago scores 0. Synthetic names." | The reason text matches the design table exactly. |
| 7:15 | Same page → click the recording link (2 min 23 s) — play ~20 s of AC4/AC5 | "Seventh visit on Monday blocked with a message; the overdue Segment A warning disappears when she is added to the plan." | `Monday already has 6 visits (max 6)`; `Dr Isla Xu (Segment A) is 51 days overdue and not planned`. |
| 7:40 | Same page → §3 *Traceability* and §4 *Not covered* → then `APPROVED` in the session | "Every AC maps to a pytest and a Vitest test, and it says what was **not** covered. QA approves — 12 min 47 s in the pre-run, 2½ minutes of it the browser run." | Honest *Not covered* section (container UI run, non-default config, screen readers). |

### 8:00 — Release: you are the Release Manager (1 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 8:00 | Tab 7 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41026121962 | "Phase 5: there is no cloud target in this demo, so the deploy workflow builds the image, smoke-tests it and pushes it to GitHub's registry — and Devin said so rather than pretending." | Workflow *Deploy navigator (non-prod)*: job *Build image + smoke test* → job *Push to GHCR (non-prod)* running inside GitHub Environment **`non-prod`**. |
| 8:20 | Same run → the *Push to GHCR (non-prod)* job (with the required reviewer set, GitHub Actions shows **Review deployments** → approve) | "The push job only runs inside the `non-prod` environment, and that environment has a required reviewer — the Release Manager clicks approve here. Devin cannot grant itself that permission; a repo admin set it." | Image `ghcr.io/amitmanchella-cog/gsk-scale-ai-demo/navigator` tagged `:<sha>`, `:pr-<n>` on PRs, `:non-prod` on `main`. If the reviewer was **not** set, say: "in this repo the gate is not yet configured, so this run went straight through — the workflow is written for the gate." |
| 8:40 | Tab 6 — https://cog-gtm.atlassian.net/browse/MBA-3650 | "And the ticket closes itself: status Done, five sub-tasks Done, one final comment with every link — PR, docs, workflow run, image." | Comments on the Story: one per phase gate, then the final link list. **Prompt-to-Done: 80 min 32 s**, ~20 s of approver think time per gate. |

### 9:00 — Governance close (1 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 9:00 | Tab 6 (Jira comments) + tab 3 side by side | "Phase gates are **human approvers** — Product Owner, Tech Lead, QA, Release Manager — not Devin approving Devin. Every gate is a Jira comment and a session message." | Four people, five gates, two audit trails. |
| 9:20 | Tab 4 — branch name and CI | "Branches are all `devin/*`; the PR is the human review gate; CI is the machine gate — lint, tests, a 90 % coverage floor on the scoring logic, a container build." | Same lifecycle as a human engineer's change. |
| 9:35 | Tab 3 — child sessions list | "Child sessions are scoped to one repo and one story, with ACU caps; the same prompt becomes a **playbook** so any team or SI runs this SDLC the same way, and an **Automation** can start it from a Jira transition." | Managed infrastructure and governance, not a hero engineer. |
| 9:50 | Tab 2 — the live session | "This is where the live run has got to since minute one. That is UC4: build the product. UC3 keeps it running." | Hand-off to UC3. |

## Hybrid approach — live start, pre-run finish (read this first)

A full SDLC does **not** fit in 10 minutes. Observed in the fallback run on 2026-10-30 (wall clock, including
~20 s of approver think time per gate):

| Phase | Duration | Notes |
|---|---|---|
| 1 Requirements | **4 min 07 s** | 07:06:31 → 07:10:38 UTC; PO approved 07:10:55 |
| 2 Design | **3 min 19 s** | 07:10:55 → 07:14:14; TL approved 07:14:35 |
| 3 Build | **54 min 35 s** | 07:14:35 → 08:09:10; children S2 → S1 ∥ S3 → S4 ∥ S5; PRs #9–#13 into `devin/MBA-3650`; final PR #14, 3 CI jobs green |
| 4 Verify | **12 min 47 s** | 08:09:10 → 08:21:57; AC1–AC6 recorded in one 2 min 23 s browser run; QA approved 08:22:26 |
| 5 Release | **4 min 37 s** | 08:22:26 → 08:27:03; deploy workflow green, image on GHCR, ticket Done |
| **Total** | **80 min 32 s** | prompt → Done; 84 backend + 23 frontend tests |

So the plan is:

1. **1:00** — start the live run (Prompt B, MBA-3651) and leave it in tab 2.
2. **~2:00–3:30** — let it reach the **requirements gate live** (~4 min in the pre-run; fill with the 0:00 ticket
   walk-through and the first steps of the plan). Read `requirements.md` and the sub-tasks **live**, reply
   `APPROVED` **live**. This is the one gate the audience sees end to end.
3. **3:30** — switch tabs to the pre-run session https://devin-gtm.devinenterprise.com/sessions/df5a35cb1f09422ea4363ec7efc72af7
   and PR https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/14 and walk design → build → verify → release
   from the artefacts on branch `devin/MBA-3650` and the Jira ticket MBA-3650.
   **Say when switching:** *"The build phase alone takes about an hour, so this is the same prompt run earlier today
   on an identical ticket — same repo, same scaffold commit — so we can see the end of the story. The live one is
   still working in the other tab."*
4. **9:50** — come back to the live session and show where it has got to (typically: design written, or the
   phase-2 gate waiting for the Tech Lead). Offer to share the PR link after the call.

If the live run reaches the design gate before 9:50, approve it live as the Tech Lead — it is a bonus, not a plan.

## Fallback — if something misbehaves

> **Do not wait on screen for more than ~30 seconds.** Switch to tab 3 / tab 4 and narrate the pre-run; come back
> to the live session at 9:50.
>
> - **Devin is slow to reach the requirements gate:** say *"Phase 1 took four minutes this morning — let me show you
>   what it produced while this one catches up"* and open the fallback
>   [requirements.md](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/requirements.md)
>   and the MBA-3650 sub-tasks. Approve the live gate whenever it lands, even mid-sentence.
> - **Jira MCP is down:** the prompt already covers it — Devin falls back to `docs/uc4/PRD.md` and writes each
>   "Jira comment" to `docs/uc4/jira-comments/<phase>.md`. Say *"the integration is the convenience, the gate is the
>   governance — the artefact and the approval still happen"*, and show the Jira trail on MBA-3650 (tab 6) instead.
> - **CI is red on the fallback PR #14:** open the green run on tab 7 and the CI checks recorded in
>   [test-report.md §1](https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/devin/MBA-3650/docs/uc4/test-report.md);
>   say *"a red check is exactly what UC3 is for"* and move on. Never re-run or push anything on stage.
> - **The live session asks a question:** if it is a **phase gate**, read the artefact and answer as the approver
>   (`APPROVED`, or a one-line change request if you want to show that path). If it is **not** a gate (a
>   clarification, a tooling choice, "shall I continue?"), answer as the Product Owner in one line or say
>   **`proceed`**. Never answer with a secret or a credential.
> - **The live session errors or stalls:** leave it; do not restart it on stage. The pre-run is the story.

> **Never approve a phase yourself — the presenter plays GSK's approvers (Product Owner, Tech Lead, QA, Release
> Manager).** Read the artefact aloud, then type `APPROVED`. That is the point of the demo: Devin never approves
> Devin.

## Why this matters for GSK

> **One repo, one story.** UC1 built the data (tested PySpark job from a notebook) → UC4 builds the product on it
> (this demo: a Jira PRD becomes a working, tested, deployable app) → UC3 runs it (an Automation that self-heals CI).
> The same synthetic field-force tables flow through all three.
>
> **Devin is managed infrastructure and governance.** Phase gates with named human approvers, `devin/*` branches, PR
> review, CI with a coverage floor, a GitHub Environment with a required reviewer, ACU caps per session and an
> auditable Jira trail — configured once, applied to every ticket.
>
> **It scales org-wide through playbooks and Automations.** Prompt B becomes a playbook; a Jira transition (e.g.
> *Ready for Dev*) becomes an Automation trigger. Every team and every SI partner gets the same SDLC, the same
> artefacts and the same gates without re-learning them.
>
> **It helps less-experienced engineers and SI partners ship safely.** The standard — stories with traceability,
> a reviewed design, tests before merge, a recorded verification, a gated release — is carried by the prompt and the
> platform, not by the seniority of the person who started the session.
>
> **It complements GSK's agentic factory; it does not compete with it.** The factory decides *what* to build and
> *which* agents to use; Devin is the governed execution engine for the software-delivery lifecycle those decisions
> produce, callable through its API.
>
> **Synthetic data only.** Every HCP, rep, visit and territory in this repo comes from a seeded generator — no real
> people, products or CRM data.

## After the call

- Leave **MBA-3651** exactly as the live run left it (comments, sub-tasks, status) — it is the recording's evidence.
- Do **not** merge the live PR into `main` without a human review; `main` should stay at the clean scaffold until a
  reviewer decides otherwise.
- The fallback PR https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/14 **stays open** (label
  `uc4-fallback`); the fallback session and branch `devin/MBA-3650` stay as they are for the next run of this demo.
- If the live session is still running, let it finish on its own; its ACU cap bounds the cost.

## FAQ / likely questions

| Question | Answer |
|---|---|
| Did Devin approve its own phases? | **No.** It stopped at the end of phases 1, 2 and 4 and resumed only on the exact reply `APPROVED` from a human — the presenter playing PO, Tech Lead and QA. The release job is gated by a GitHub Environment required reviewer (Release Manager). |
| Is this real HCP data? | No — all synthetic, generated by a seeded script (`data/generate.py`); 1,600 HCPs, 30 reps, 20 territories. |
| How long does the full SDLC take? | **80 min 32 s** prompt-to-Done in the pre-run, of which the build phase was 54 min; the gates themselves took ~20 s of think time each. |
| Where did it deploy? | Nowhere yet — no cloud target exists in this demo. The deploy workflow builds, smoke-tests and pushes the image to GHCR (`ghcr.io/amitmanchella-cog/gsk-scale-ai-demo/navigator`) from a job inside the `non-prod` GitHub Environment. Pointing it at AKS or App Service is a workflow change, not an app change. |
| Why child sessions? | One story, one sub-task, one branch, one PR, one ACU cap each; the parent sequences them by dependency (scoring first) and merges them. Blast radius and cost are bounded per story. |
| What if the Jira integration fails? | The prompt tells Devin to read `docs/uc4/PRD.md` and write the phase comments to `docs/uc4/jira-comments/`. The gates still happen in the session. |
| How does this become the standard? | Prompt B becomes a **playbook**; a Jira status transition becomes an **Automation** that starts the session. Teams and SIs then run the same SDLC without knowing the prompt. |
| Who merges? | A human. Devin opens the PR; CI (lint, tests, 90 % scoring coverage, container build) must be green; a reviewer merges. Devin never merges to `main`. |
