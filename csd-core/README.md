# csd-core

Pure Python 3.11 domain core of the computable study design demo. A clinical study is held
as two linked graphs that are versioned together, instead of as text:

- **Intent graph**: objectives, estimands, endpoints (each with a timepoint such as
  "Week 12"), design activities (for example spirometry), arms and assignment.
- **Plan graph**: the patient journey (visits with a study day and window), operational
  activities with a unit cost and duration, operational standards and the schedule of
  activities (which activity happens at which visit).

Every change is a typed operation that creates a new immutable version with a parent link.
All data is synthetic. No person-level data is stored.

## Layout (ports and adapters)

```
src/csd_core/
  domain/        models, operations, structural validity, findings, versions   (no I/O)
  ports/         VersionStore protocol
  adapters/      InMemoryVersionStore
  application/   StudyService: create_study, apply, history, replay
  reference/     the synthetic Phase 3 asthma reference study and the seeded defect catalogue
```

The core imports no storage, web or agent framework. `lint-imports` enforces this and the
layering in CI (see `[tool.importlinter]` in `pyproject.toml`).

## Run

```bash
cd csd-core
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check . && ruff format --check .   # lint
mypy                                    # types (strict)
lint-imports                            # import contracts
pytest                                  # unit + Hypothesis property tests, with coverage
pip-audit                               # dependency audit
```

## Use

```python
from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.application.study_service import StudyService
from csd_core.domain.operations import MoveVisit
from csd_core.reference.asthma import REFERENCE_STUDY_ID, reference_study

service = StudyService(InMemoryVersionStore())
v0 = service.create_study(REFERENCE_STUDY_ID, reference_study())
v1 = service.apply(v0.id, MoveVisit(visit_id="V-W12", day=99))
assert v1.parent_id == v0.id  # new immutable version, parent unchanged
assert service.replay(v1.id) == v1.graph
```

## Operations

`AddVisit`, `MoveVisit`, `SetVisitWindow`, `RemoveVisit`, `AddActivity`, `ScheduleActivity`,
`UnscheduleActivity`, `AddObjective`, `AddDesignActivity`, `AddEndpoint`,
`ChangeEndpointTiming`, `ChangePrimaryEndpoint`, `AddArm`.

An operation is applied to the head version of a branch. If it does not fit the graph, or
its result would break a structural validity rule (unique IDs, exactly one primary endpoint,
no dangling references, unique visit days, no Day 0), `OperationError` is raised and no
version is created.

## Findings

After every operation the intent-vs-plan rules are recomputed and stored on the new version
(`Version.findings`). Findings are warnings and never block an operation.

| Type | Meaning |
|---|---|
| `untraced_activity` | A scheduled activity traces to no design activity or operational standard |
| `unmet_endpoint_timepoint` | No visit within its window of the endpoint's timepoint day performs the activity the endpoint needs |
| `missing_operational_standard` | A visit is missing a required standard activity (consent and eligibility at screening, vital signs at every on-site visit, adverse event review at every visit after randomisation) |

The reference study has zero findings. `csd_core.reference.defects.DEFECT_CATALOGUE` holds 26
seeded broken variants (8 untraced, 10 unmet timepoint, 8 missing standard), each with the
exact finding IDs it must produce; the tests assert all of them.

### Flagship scenario

```python
v1 = service.apply(v0.id, MoveVisit(visit_id="V-W12", day=99))
[f.id for f in v1.findings]  # ['unmet_endpoint_timepoint:EP-FEV1'] (a warning, the version exists)
v2 = service.apply(v1.id, ChangeEndpointTiming(endpoint_id="EP-FEV1", week=14))
v2.findings  # () Week 14 is Day 99
```

`csd_core.domain.schedule.schedule_grid(graph)` returns the schedule-of-activities grid
(activities as rows, visits by study day as columns).

## Conventions

- An endpoint timepoint is a study week. Its target day is `7 x week + 1` (Week 12 = Day 85).
- Version IDs are deterministic hashes of (study, parent, branch, operation).

## Branches, scores and compare

```python
service.create_branch(root.id, "fewer-visits")            # from any version, head or not
fewer = service.apply(root.id, RemoveVisit(visit_id="V-W4"), branch="fewer-visits")
service.score(fewer.id)        # visit_count=6, patient_time_minutes=550, cost_proxy=1940
service.compare(root.id, fewer.id)   # both scores, both findings, delta, element changes
```

- A branch starts with its base version as its head and creates no version. The first
  operation names the branch; later ones follow the version's own branch.
- Scores (lower is better): visit count; total patient time, the sum of visit durations
  where a visit lasts as long as the activities scheduled at it; cost proxy, the sum of
  the unit costs of every scheduled activity, per participant.
- The reference study scores 7 visits, 640 minutes and 2160.
