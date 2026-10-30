# UC1 demo flow — "Build the data": messy notebook → tested PySpark job

**Length:** 10 minutes · **Audience:** GSK data-engineering and platform leads, SI partners, AI/agentic-factory owners
· **Story position:** UC1 *build the data* → UC4 *build the product* → UC3 *run it*

**Premise.** A field-force analyst wrote a quick notebook that mixes pandas and PySpark, hard-codes paths and ends
with `toPandas()` so it can never run at scale. Data engineering has a backlog of hundreds of these. Devin, driven by
a **playbook** that codifies GSK's engineering standard, turns the notebook into a modular PySpark job with unit
tests, data-quality gates, a Databricks job definition and a parity check that proves the output did not change —
and hands it over as a normal pull request that CI and a human reviewer gate. Everything shown is synthetic data.

## Before you start (5 minutes before the call)

Pre-open these tabs, left to right, in this order:

| # | Tab | URL |
|---|---|---|
| 1 | "Before" notebook (rendered on GitHub) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/notebooks/territory_kpis.ipynb |
| 2 | Merged UC1 PR — *Files changed* tab | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/2/files |
| 3 | Green CI run for the PR (parity line lives in the *Pipeline parity (UC1)* step) | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011065616 |
| 4 | Databricks job JSON | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/jobs/territory_kpis.json |
| 5 | Playbook page — **Notebook to PySpark job** (used to start the live run) | https://devin-gtm.devinenterprise.com/settings/playbooks/9e1fef4a89a84b19901df5f30c3078e6 |
| 6 | **Pre-run session A** (the conversion that produced PR #2 — your fallback) | https://devin-gtm.devinenterprise.com/sessions/91a1d13228e543a88dd2c86a8dc7ace4 |
| 7 | Second "before" notebook for the live run | https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/notebooks/hcp_engagement.ipynb |

Checklist:

- [ ] Signed in to https://devin-gtm.devinenterprise.com and the playbook page (tab 5) loads.
- [ ] Tab 6 (session A) scrolls; you know where its final PR link is.
- [ ] Tab 3 shows a green check; expand *Pipeline parity (UC1)* and confirm the last line is `520 rows compared, 0 mismatches`.
- [ ] Prompt below is in your clipboard (see 4:00).
- [ ] Confirm `pipelines/hcp_engagement/` does **not** already exist on `main` (if a previous rehearsal merged it, the live run has nothing to do — pick a fresh branch/notebook or delete the folder on a branch first).
- [ ] Say "synthetic data" at least once; never describe it as GSK data.

## Main flow (10 minutes)

### 0:00 — The messy notebook (1.5 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 0:00 | Tab 1 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/notebooks/territory_kpis.ipynb | "This is the typical starting point: an analyst's weekly territory-KPI notebook that works on a laptop and nowhere else." | The markdown header literally says *"TODO: clean up before handing to data eng"*. |
| 0:20 | Scroll to cell 1–2 (imports + loads) | "pandas **and** PySpark in the same notebook, whichever was quicker at the time; `DATA = '../data'` hard-coded." | `pd.read_parquet` and `spark.read.parquet` side by side; `# TODO parametrise`. |
| 0:50 | Scroll to the *sales in spark* cell | "Sales are aggregated in Spark — then pulled back with `toPandas()` for the joins, so the job can never scale past one machine." | `.toPandas()` in the middle of the pipeline. |
| 1:10 | Scroll to the bottom | "No functions, no tests, no data-quality checks, output path hard-coded. There are hundreds of these across any pharma commercial org." | `kpis.to_parquet('expected_output/…')` — the output we will treat as the frozen contract. |

### 1:30 — The merged PR: what Devin shipped (2.5 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 1:30 | Tab 2 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/2/files | "Devin converted it into a proper job and opened a PR — same KPI table, now engineered." | File tree: `pipelines/territory_kpis/` with `config.py`, `extract.py`, `transform.py`, `quality.py`, `load.py`, `job.py`, `parity.py`, `tests/`, `README.md`; plus `jobs/territory_kpis.json`. |
| 1:50 | Click `transform.py` — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/pipelines/territory_kpis/transform.py | "Pure DataFrame functions — `aggregate_visits`, `aggregate_open_follow_ups`, `aggregate_sales`, `assemble_kpis` — no `toPandas`, no `collect`." | One small function per step; `round_half_even` reproduces the notebook's pandas rounding so results match exactly. |
| 2:20 | Click `tests/` — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/tree/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/pipelines/territory_kpis/tests | "39 tests: a unit test per transform on tiny hand-built DataFrames, a pass **and** fail case for every DQ check, config overrides, and an end-to-end run against the frozen notebook output." | `test_transform.py`, `test_quality.py`, `test_config.py`, `test_extract_load.py`, `test_job_e2e.py`. |
| 2:45 | Click `quality.py` — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/pipelines/territory_kpis/quality.py | "Data-quality gates run before the write: schema, no null keys, unique `(territory_id, week)`, row-count bounds — any failure raises and nothing lands downstream." | `check_schema`, `check_no_null_keys`, `check_unique_keys`, `check_row_count`, `DataQualityError`. |
| 3:10 | Tab 3 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011065616 → expand *Pipeline parity (UC1)* | "And the proof: CI re-runs the job and compares every column with the notebook's frozen output." | Last line: **`520 rows compared, 0 mismatches`**. Also the `Lint` (ruff) and `Tests` (pytest) steps above it. |
| 3:35 | Tab 4 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/jobs/territory_kpis.json | "Deployment is a Databricks Jobs 2.1 definition — weekly `spark_python_task` from Git, 1-worker job cluster, failure notifications, dependent parity task. Shown, not run: no Databricks account is involved in this demo." | `"quartz_cron_expression": "0 0 6 ? * MON"`, `spark_python_task` → `pipelines/territory_kpis/job.py`, `max_concurrent_runs: 1`. |

### 4:00 — LIVE: run the playbook on a second notebook (3 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 4:00 | Tab 7 — https://github.com/amitmanchella-cog/gsk-scale-ai-demo/blob/1776de8fc9775e8ab908fbf7a8c7db59b33744c9/notebooks/hcp_engagement.ipynb | "Here is a second analyst notebook — HCP engagement, same mess, still unconverted. Let's do it live." | `toPandas()` three times, `DATA = '../data'`, hard-coded `AS_OF` date. |
| 4:30 | Tab 5 — https://devin-gtm.devinenterprise.com/settings/playbooks/9e1fef4a89a84b19901df5f30c3078e6 | "The standard lives in a playbook — module layout, tests, DQ gates, parity, PR conventions. Anyone in the org starts from it." | Playbook body: the same steps you just saw in the PR. |
| 5:00 | Start a session **from the playbook**: on the playbook page click *Use playbook* / *New session* (or open a new session, pick **Notebook to PySpark job** from the playbook picker), select repo **amitmanchella-cog/gsk-scale-ai-demo**, paste the prompt below, start. | "One prompt: which notebook, where to put it, the parity key and the frozen output to match. Everything else comes from the playbook." | Prompt is four facts long — the playbook carries the engineering standard. |
| 5:30 | Watch Devin's first steps in the new session | "It is reading the notebook and planning: modules → tests → DQ → parity → PR → CI." | The plan appears before any code is written. |
| 6:00 | Point at the branch name once Devin creates it | "Branch prefix `devin/`, PR against `main`, CI gates — same lifecycle as a human engineer." | Session is scoped to one repo; no credentials typed. |

**Prompt to paste (verbatim):**

```
Convert notebooks/hcp_engagement.ipynb into pipelines/hcp_engagement/ following the playbook; parity key hcp_id; expected output notebooks/expected_output/hcp_engagement.parquet
```

If you start from a blank new-session box instead of the playbook page, prefix the prompt with
`[Used playbook: Notebook to PySpark job]` so the playbook is attached.

### 7:00 — What Devin is doing while it runs (2 min)

Keep the live session on screen; switch to **tab 6 (session A)** to narrate the finished shape if the live run is
still reading or writing modules.

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 7:00 | Live session (plan / first files) | "Step 1 — read the notebook cell by cell and list every semantic it must preserve: week = Monday, joins, rounding." | Devin states assumptions explicitly instead of guessing. |
| 7:30 | Tab 6 — https://devin-gtm.devinenterprise.com/sessions/91a1d13228e543a88dd2c86a8dc7ace4 (scroll to the middle) | "This is the same playbook on the first notebook, pre-run. Step 2 — modules; step 3 — tests on tiny DataFrames; step 4 — DQ checks; step 5 — parity against the frozen parquet." | Devin runs `ruff`, `pytest` and `parity.py` **itself** before opening the PR. |
| 8:00 | Tab 6 — scroll to where the rounding fix (`round_half_even`) is discussed | "It hit a real gotcha — pandas rounds half-to-even, Spark rounds half-up, 30 cells differed — found it through the parity check and fixed it. That is why the parity gate exists." | The loop: run parity → mismatch → fix → `0 mismatches`. |
| 8:30 | Tab 6 — final message with the PR link → tab 2 | "Step 6 — PR with a description a reviewer can read; step 7 — CI green. The human reviews and merges; Devin does not." | PR #2 is the artefact; merge was a human click. |

### 9:00 — Governance close (1 min)

| Minute | Click (exact URL) | SAY (one line) | Audience should notice |
|---|---|---|---|
| 9:00 | Tab 5 (playbook) | "The playbook **is** the codified standard. Change it once and every future conversion follows the new rule — this is how it scales to hundreds of notebooks and to SI teams." | Standard is versioned text, not tribal knowledge. |
| 9:20 | Tab 3 (CI run) | "Three gates on every PR — `ruff`, `pytest`, parity versus the frozen notebook output — all on local Spark in GitHub Actions. No credentials, no Databricks account." | `Lint`, `Tests`, `Pipeline parity (UC1)` steps. |
| 9:40 | Tab 2 (PR) | "Branch naming `devin/*`, PR review as the human gate, repo-scoped sessions. Devin is managed infrastructure for your engineers, not a replacement for your review process." | Devin's PR looks like any engineer's PR. |
| 9:55 | — | "That is UC1: build the data. UC4 builds the product on top of these tables; UC3 keeps it running." | Hand-off to the next use case. |

## Fallback — if the live run is slow or stalls

> **Do not wait on screen for more than ~30 seconds.** Say: *"Conversions take 10–20 minutes end to end; I pre-ran
> the exact same playbook on the first notebook this morning — let me show you that run while this one works."*
>
> 1. Switch to **session A**: https://devin-gtm.devinenterprise.com/sessions/91a1d13228e543a88dd2c86a8dc7ace4 —
>    scroll top to bottom: plan → modules → tests → the rounding gotcha found by parity → fix → PR.
> 2. Switch to the **merged PR**: https://github.com/amitmanchella-cog/gsk-scale-ai-demo/pull/2 — read the
>    *Verification* section of the description (`39 passed`, `520 rows compared, 0 mismatches`).
> 3. Switch to the **CI run**: https://github.com/amitmanchella-cog/gsk-scale-ai-demo/actions/runs/41011065616 —
>    the same numbers, produced by GitHub Actions, not by Devin's own claim.
> 4. Come back to the live session at 9:00 for whatever it has produced so far (branch, first modules, tests) and
>    offer to share the PR link after the call.

## Why this matters for GSK

> **One repo, one story.** UC1 builds the data (this demo) → UC4 builds the product (the Field Force Navigator
> from a Jira PRD) → UC3 runs it (an Automation that self-heals CI). The same synthetic field-force tables flow
> through all three.
>
> **Devin is managed infrastructure and governance.** The engineering standard lives in a **playbook**; recurring
> work is triggered by **Automations**; sessions are repo-scoped and gated by CI and PR review. That is what makes
> it scale org-wide rather than one hero engineer at a time.
>
> **It helps less-experienced engineers and SI partners ship safely.** The playbook carries the standard — module
> layout, tests, DQ gates, parity — so the person starting the session does not have to know it.
>
> **It complements GSK's agentic factory; it does not compete with it.** The factory defines *what* to build and
> *which* agents to use; Devin is a governed execution engine that factory workflows can call for software-delivery
> tasks like this one.
>
> **Synthetic data only.** Every table in this repo is generated by a seeded script — no real people, products,
> places or CRM data.

## FAQ / likely questions

| Question | Answer |
|---|---|
| Does this need Databricks? | **No.** Tests and parity run on **local Spark** inside GitHub Actions CI; `jobs/territory_kpis.json` is a Databricks Jobs 2.1 definition that is **shown, not run**. No Databricks account or credentials are used anywhere in the demo. |
| Is this real GSK data? | No — all synthetic, generated by a seeded script (`data/generate.py`); ~10k rows across six tables. |
| How do you know the output didn't change? | `parity.py` aligns the job output with the notebook's frozen parquet on `territory_id + week` and compares every column; CI prints `520 rows compared, 0 mismatches` and fails the build on any mismatch. |
| How does this scale to hundreds of notebooks? | The **playbook** is the standard; an **Automation** can start a session per notebook (e.g. from a Jira ticket or a folder listing), each repo-scoped with an ACU cap, each ending in a PR for human review. |
| What about the agentic factory? | Complementary. The factory orchestrates and decides; Devin is a governed execution engine for the software-delivery steps, callable through its API. |
| Who approves the change? | A human. Devin opens the PR on a `devin/*` branch; CI (ruff, pytest, parity) must be green; a reviewer merges. Devin does not merge. |
| What if the notebook has a bug? | Parity preserves the notebook's semantics exactly (including its rounding), so the bug is reproduced faithfully and visible in a reviewable, tested module — fix it there, with a test. |
| How long does a conversion take? | Roughly 10–20 minutes of session time for a notebook of this size, plus CI (~1–2 minutes). |
| What does the engineer still need to know? | Which notebook, where it should live, the parity key and the frozen expected output — the four facts in the prompt. The playbook supplies the rest. |
