# UC3 demo flow — "Run it": CI self-healing with a Devin Automation

**Length:** 8 minutes · **Audience:** GSK platform / DevOps leads, SI partners, agentic-factory owners
· **Story position:** UC1 *build the data* → UC4 *build the product* → UC3 *run it*

**Story recap (3 lines).** UC1 turned analyst notebooks into tested PySpark jobs (`pipelines/`, `notebooks/`).
UC4 built the Field Force Navigator product from Jira tickets. UC3 keeps all of it running: a Devin **Automation**
watches CI on this repo and, when a pull request goes red, diagnoses, reproduces, writes a regression test, fixes and
comments — inside hard governance limits. The target is `services/supply_api/`, a synthetic FastAPI *clinical supply
forecast* service (FastAPI + Pydantic v2, 11 endpoints, zoneinfo date handling, 34 tests, seeded data via
`random.Random(42)`; merged in https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/1). Synthetic data only.

## Pre-demo checklist (do this the day before)

At the time of writing PRs A, B and C are red but the Automation has **not yet fired** on any of them — the GitHub
`check_run` webhook delivery to Devin still needs to be verified. Work through this list in order:

1. Open the Automation page https://devin-gtm.devinenterprise.com/automations/b09f21a5803c4fb69d049070a961ef94 and confirm it shows **Enabled**.
2. In the GitHub repo **Settings → GitHub Apps** (Devin integration), confirm the **check_run** event is delivered to Devin. If it is not, re-install the Devin GitHub App on `amitmanchella-cog/gsk-scale-ai-demo`.
3. On PR A and PR B, open the failed Actions run (links in the tab table below) and click **Re-run jobs → Re-run failed jobs** to re-emit the `check_run` failure event.
4. Within ~2 minutes a session should appear under the Automation (or at https://devin-gtm.devinenterprise.com/sessions?tags=uc3-self-heal — if that filter URL does not resolve, open https://devin-gtm.devinenterprise.com/sessions and filter by tag `uc3-self-heal`). Let both sessions finish, confirm PR A and PR B are green with one Devin comment each, then **replace `<<SESSION_URL_A>>` and `<<SESSION_URL_B>>` in this doc** with the real session URLs.
5. Leave **PR C red and untouched**. If the Automation fires on C by accident, terminate that session and reset branch `chore/bump-defaults` to its single commit `eba1e1c` (`git push --force origin eba1e1c:chore/bump-defaults`).
6. Verify PR C has **no Devin comments** and still shows exactly one commit.
7. Rehearse the live re-run once on PR A (not C): confirm a session appears in under 2 minutes. If it does not, plan to use the Fallback box.

### Tabs to pre-open (left to right)

| # | Tab | URL |
|---|---|---|
| 1 | Automation config page | https://devin-gtm.devinenterprise.com/automations/b09f21a5803c4fb69d049070a961ef94 |
| 2 | PR A — *Simplify report date parsing* (timezone bug, fixed by Devin) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/3 |
| 3 | PR A Automation session | `<<SESSION_URL_A>>` |
| 4 | PR B — *Rename forecast helper for clarity* (ImportError, fixed by Devin) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/4 |
| 5 | PR B Automation session | `<<SESSION_URL_B>>` |
| 6 | PR C — *Bump default lead time to 8 weeks* (**red, untouched — the live one**) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/5 |
| 7 | Sessions list filtered by tag `uc3-self-heal` | https://devin-gtm.devinenterprise.com/sessions?tags=uc3-self-heal |
| 8 | GitHub Actions runs page | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions |

Failed CI runs as of writing (re-run from here in step 3): PR A https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011221592 ·
PR B https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011228195 ·
PR C https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011264396

## Main flow (8 minutes)

### 0:00 — The Automation: what watches the repo (1.5 min)

| Minute | Where (exact URL) | Click | SAY (one line) | NOTICE |
|---|---|---|---|---|
| 0:00 | Tab 1 — https://devin-gtm.devinenterprise.com/automations/b09f21a5803c4fb69d049070a961ef94 | Open the page | "This is **GSK Demo — UC3 CI Self-Heal**: not a chatbot, a managed Automation that reacts to a GitHub event with a fixed prompt and fixed limits." | Name, **Enabled** state, event type `github:check_run`. |
| 0:20 | Same page — trigger conditions | Scroll to the trigger block | "It fires only when a CI check **completes with conclusion failure**, only in this repo, and only on branches that are not `main` and do not contain `devin/`." | `action = completed`, `conclusion = failure`, `repository.full_name = amitmanchella-cog/gsk-scale-ai-demo`, `head_branch != main`, `head_branch not_contains "devin/"`. |
| 0:40 | Same page | Point at `not_contains "devin/"` | "That branch exclusion is loop protection: Devin pushes to the PR's existing branch, so its own work can never re-trigger the Automation and chain-react." | Also: Devin never opens a new PR from this Automation, so there is no second branch to trigger on. |
| 0:55 | Same page — limits | Scroll to limits | "Every run is capped at **10 ACUs**, at most **6 runs an hour**, **3 concurrent**, queue depth **5** — the cost ceiling is known before anything happens." | Sessions are tagged `gsk-demo` + `uc3-self-heal` for reporting. |
| 1:10 | Same page — network policy | Scroll to allowlist | "The sandbox can reach only GitHub, PyPI and Devin's git manager — nothing else on the internet." | `github.com`, `api.github.com`, `*.githubusercontent.com`, `pypi.org`, `files.pythonhosted.org`, `git-manager.devin.ai`. |
| 1:20 | Same page — prompt | Scroll to prompt | "And the prompt is the engineering standard: diagnose from logs → reproduce with the same CI command → write a regression test that fails first → smallest fix → push only to the PR's branch → one root-cause comment. It must never skip, xfail or weaken a test, never edit CI or dependency pins unless they *are* the bug, and must stop and comment if the failure is infrastructural." | "never main, never a new PR, never force-push". |

### 1:30 — PR A: a timezone bug, found and fixed while nobody was looking (2 min)

| Minute | Where (exact URL) | Click | SAY (one line) | NOTICE |
|---|---|---|---|---|
| 1:30 | Tab 2 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/3 | Open **Conversation** tab, scroll to the first commit's CI status | "A developer 'simplified' date parsing in the clinical-supply service and CI went red on two tests." | Commit `066d8b0`; check **Python lint + tests (data, pipelines, services)** failed; failing tests `test_offset_datetime_resolves_to_next_day_in_tokyo`, `test_report_uses_site_local_dates`. |
| 1:50 | Same PR | Scroll to the Devin comment | "The bug in one sentence: a consumption report that ends at 11:30 pm New York time was being filed under the **UTC** date, so for a Tokyo trial site it landed on the wrong day and the wrong week — the kind of thing that quietly mis-counts drug supply." | Comment structure: root cause → change → regression test → commands + results. |
| 2:20 | Tab 3 — `<<SESSION_URL_A>>` | Open the session; scroll to the test step | "Devin first wrote a regression test and showed it **failing** on the broken code — then fixed `to_site_local_date()` to use the site's timezone again." | The failing-then-passing `pytest` output in the transcript; the same CI command (`ruff check .` then `pytest`) run locally. |
| 2:50 | Tab 2 — PR A **Files changed** | Click **Files changed** | "One small fix in `services/supply_api/app/dates.py`, one new test, pushed to the developer's own branch — no new PR, no touch on `main`." | Fix commit is by Devin on branch `fix/report-date-parsing`; green check on the latest commit. |
| 3:15 | Same PR | Point at the green check | "Red to green with a reviewable audit trail, zero human minutes." | Human still merges — Devin never does. |

### 3:30 — PR B: a refactor that broke imports (1 min)

| Minute | Where (exact URL) | Click | SAY (one line) | NOTICE |
|---|---|---|---|---|
| 3:30 | Tab 4 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/4 | Open **Conversation** tab | "Different failure class: a rename (`moving_average` → `rolling_mean`) updated the caller but not the tests, so the whole test module failed to **import** — nothing ran." | `ImportError` at collection in `tests/test_forecast.py`; commit `f0655f9`. |
| 3:50 | Tab 5 — `<<SESSION_URL_B>>` | Skim | "Same playbook: read the CI log, reproduce, regression test, smallest fix, one comment — Devin kept the author's intent (the rename) rather than reverting it." | Fix is on branch `refactor/forecast-naming`; Devin comment lists the exact commands. |
| 4:15 | Tab 4 | Point at green check | "Two different bugs, one Automation, same guardrails." | — |

### 4:30 — LIVE: trigger it on PR C (2 min)

| Minute | Where (exact URL) | Click | SAY (one line) | NOTICE |
|---|---|---|---|---|
| 4:30 | Tab 6 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/5 | Open the PR | "This one is still red and nobody has touched it: a config PR that bumped the default reorder lead time from 6 to 8 weeks." | One commit `eba1e1c`, red check, **no Devin comment**. |
| 4:45 | Same PR | Click the **Checks** tab → click the failed **Python lint + tests (data, pipelines, services)** check → click **View workflow run** (opens the Actions run) → top-right **Re-run jobs ▾** → **Re-run failed jobs** → confirm **Re-run jobs** in the dialog | "I'm re-running the failed job so GitHub re-emits the failure event — exactly what a fresh push would do." | The run restarts (yellow dot). It takes ~1 minute to fail again; keep talking. |
| 5:15 | Tab 1 (Automation page, runs/sessions section) or Tab 7 — https://devin-gtm.devinenterprise.com/sessions?tags=uc3-self-heal | Refresh | "As soon as the check reports *failure*, the Automation spawns a session — tagged, capped at 10 ACUs, scoped to this repo." | New session appears with tags `gsk-demo`, `uc3-self-heal`. |
| 5:45 | Open the new session | Watch the first steps | "It is reading the CI log, cloning the branch, running `pytest` to reproduce `test_product_default_lead_time_is_six_weeks` failing, then it will write a regression test, make the smallest fix, push to `chore/bump-defaults`, and leave one comment." | Narrate each step as it appears in the transcript; it will finish after the demo — that is fine. |
| 6:15 | — | — | **If no session has appeared 90 seconds after the re-run went red, switch to the Fallback box below** and say: "The trigger is queued; here is the same flow recorded on the previous two PRs." | Do not re-run again on stage; the queue would double. |

> **Judgement call to narrate on PR C:** the failing test asserts the default is *six* weeks, so "fix" could mean
> reverting the default **or** updating the test. The prompt tells Devin to stop and comment if fixing would change
> intended behaviour — so expect it to either restore 6 weeks or ask the author which was intended, not to silently
> rewrite the test. Either outcome is the right one, and it is a great point to make about guardrails.

### 6:30 — Governance close (1.5 min)

| Minute | Where (exact URL) | Click | SAY (one line) | NOTICE |
|---|---|---|---|---|
| 6:30 | Tab 1 — https://devin-gtm.devinenterprise.com/automations/b09f21a5803c4fb69d049070a961ef94 | Scroll to limits again | "Cost: 10 ACUs per run, 6 an hour, 3 concurrent — a budget, not a blank cheque." | Queue depth 5: bursts queue, they don't fan out. |
| 6:50 | Same page | Point at repo scope + allowlist | "Blast radius: one repo, one branch per run, six allowed hosts, never `main`, never a new PR, never force-push, never a skipped or weakened test." | — |
| 7:10 | Tab 2 (PR A comment) + Tab 3 (session) | Side by side | "Audit trail: every run leaves a PR comment a reviewer can read in 30 seconds, and a full session transcript for compliance." | Root cause → change → regression test → commands + results. |
| 7:30 | Devin app — usage / analytics page (navigate from the left nav) | Open | "Usage and ACU consumption roll up per tag, so platform owners see what self-healing costs across all repos." | Filter by tag `uc3-self-heal`. |
| 7:45 | — | — | "To roll this out: the prompt becomes a **playbook**, the Automation is cloned per repo or per team, and SIs or less-experienced engineers get the standard for free — Devin is the managed infrastructure and governance layer around the agents GSK's factory already builds." | Close on *complements, not competes*. |

## Fallback box — if the trigger is slow

- Open `<<SESSION_URL_A>>` (PR A) and `<<SESSION_URL_B>>` (PR B): play the session recording or scroll the transcript — log read → reproduce → failing regression test → fix → push → comment.
- Open the Devin comments on https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/3 and https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/4 and read the *root cause* line aloud.
- Keep Tab 7 (https://devin-gtm.devinenterprise.com/sessions?tags=uc3-self-heal) open; if the PR C session appears during the close, switch back to it.
- Say: "Trigger latency is GitHub webhook delivery, not Devin — the Automation is queued and will run with the same limits."

## Azure Monitor box — the same Automation from production alerts

GSK's services already raise alerts in Azure Monitor. The same self-heal pattern applies there: an Azure Monitor alert
rule fires an **action group** whose **webhook action** posts the alert payload to Devin — either to the Devin API to
start a session, or to an Automation with an incoming-webhook trigger. The prompt and guardrails are identical
(reproduce, regression test, smallest fix, push only to a branch, one comment, never touch prod config); only the
trigger changes from "CI check failed" to "alert fired". Not wired in this demo — describe, don't click.

## Why this matters for GSK

- **Managed infrastructure + governance.** Sandboxed sessions with a network allowlist, ACU caps, rate limits and repo scope are configured once by platform owners, not re-invented per team.
- **Scales org-wide through playbooks and Automations.** The CI self-heal prompt is a playbook; cloning the Automation per repo gives every team the same standard and the same audit trail.
- **Helps less-experienced engineers and SI partners ship safely.** The guardrails (never skip a test, never edit CI, stop if infrastructural) are enforced by the platform, so quality does not depend on who wrote the PR.
- **Complements GSK's agentic factory.** GSK builds domain agents; Devin is the governed engineering agent that keeps the code, pipelines and services underneath them green. No overlap, no real GSK data — everything here is synthetic.

## Appendix — the three planted bugs

| PR | Branch | File | One-line diff | Failing test(s) |
|---|---|---|---|---|
| A — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/3 | `fix/report-date-parsing` (commit `066d8b0`) | `services/supply_api/app/dates.py` | `to_site_local_date()`: `dt.astimezone(ZoneInfo(tz_name)).date()` → `dt.astimezone(timezone.utc).date()` | `test_offset_datetime_resolves_to_next_day_in_tokyo`, `test_report_uses_site_local_dates` (`tests/test_dates_and_reports.py`) |
| B — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/4 | `refactor/forecast-naming` (commit `f0655f9`) | `services/supply_api/app/forecast.py` | `def moving_average(` → `def rolling_mean(` (caller in `forecast_consumption` updated; tests still `from app.forecast import ... moving_average`) | `ImportError` at collection — whole `tests/test_forecast.py` |
| C — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/5 | `chore/bump-defaults` (commit `eba1e1c`) | `services/supply_api/app/models.py` | `Product.lead_time_weeks: int = Field(default=6, ...)` → `Field(default=8, ...)` | `test_product_default_lead_time_is_six_weeks` (`tests/test_reorder.py`) |

**Why PR A matters to the business:** `2026-03-01T23:30:00-05:00` is 1 March in New York but already 2 March in
Tokyo. The service converts each report boundary to the *site's* local date before choosing which weeks to total; the
planted change used UTC for every site, so Tokyo's report started a week early and New York's a day late.

**CI definition:** `.github/workflows/ci.yml`, job **Python lint + tests (data, pipelines, services)** = `ruff check .` +
`pytest` (plus the UC1 parity step). Devin reproduces with exactly those two commands from the repo root.
