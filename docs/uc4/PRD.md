# PRD — Field Force Navigator: Territory Call Planner

> Exact text of Jira tickets MBA-3650 (fallback pre-run) and MBA-3651 (live demo). Project **MBA**, issue type **Story**. The UC4 fallback pre-run reads the PRD from this file.

## Problem

Field reps plan their weekly visits to healthcare professionals (HCPs) by hand from spreadsheets. They miss overdue follow-ups and spend planning time that could go to visits. District managers can't see whether plans cover the right HCPs.

## Users

Field rep: plans their own week.
District manager: reviews their reps' plans.

## Goal

A rep can build a prioritised weekly call plan for their territory in under 5 minutes.

In scope (3 features)

Territory HCP list. The rep sees the HCPs in their territory, with filters for specialty, segment (A/B/C) and days since last visit, and search by name.
Visit priority score. Each HCP gets a 0-100 score with a plain-language reason (for example, "Segment A, 45 days since last visit, 1 open follow-up"). The rules are configurable:
Segment weight: A=40, B=25, C=10.
Days since last visit: +1 per day, max 40.
Open follow-up: +20.
Visited in the last 7 days: score = 0.
Weekly plan builder. The rep adds HCPs to Mon-Fri slots, at most 6 visits a day. The app warns about duplicates and about any Segment A HCP more than 30 days overdue who is left off the plan. The plan exports as CSV.

## Out of scope

Integration with a real CRM (such as Veeva).
Real HCP data or PII.
SSO.
Mobile app.
Route optimisation.
GenAI features.

## Data

Use the curated tables produced by the UC1 PySpark job in this repo (pipelines/territory_kpis output: HCPs, visits, follow-ups, territories). Synthetic only, no real names.

## Acceptance criteria

AC1: Given a rep is selected, when the HCP list opens, then only HCPs in that rep's territory appear, and the filters and search narrow the list correctly.
AC2: Given an HCP is Segment A, 45 days since last visit, with 1 open follow-up, when its score is calculated, then the score is 100 (40 + 40 cap + 20, capped at 100) and the reason text lists all 3 factors.
AC3: Given an HCP was visited 3 days ago, when its score is calculated, then the score is 0.
AC4: Given a day already has 6 visits, when the rep adds a 7th, then the add is blocked with a message.
AC5: Given a Segment A HCP is more than 30 days overdue and not in the plan, when the rep views the plan, then a warning names that HCP.
AC6: Given a completed plan, when the rep exports it, then a CSV downloads with day, HCP, specialty, score and reason.

## Non-functional

Scoring logic has at least 90% unit test coverage.
CI runs lint, tests and a container build on every PR.
The HCP list loads in under 1 s for 300 HCPs.
Basic keyboard accessibility.

## Phase artefacts and approvers

| Phase | Artefact | Approver | |---|---|---| | Requirements | docs/requirements.md + sub-tasks | Product Owner | | Design | docs/design.md | Tech Lead | | Build | PR with tests passing in CI | Tech Lead (code review) | | Verify | docs/test-report.md + recording | QA | | Release | Gated deploy to non-prod | Release Manager |

## Definition of done

All acceptance criteria pass in the test report.
Every phase artefact is approved by its named approver.
The PR is green and linked to this ticket.
The deploy to non-prod is approved through the gate.
