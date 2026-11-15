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
  domain/        models, operations, structural validity, versions   (no I/O)
  ports/         VersionStore protocol
  adapters/      InMemoryVersionStore
  application/   StudyService: create_study, apply, history, replay
  reference/     the synthetic Phase 3 asthma reference study
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
`ChangePrimaryEndpoint`, `AddArm`.

An operation is applied to the head version of a branch. If it does not fit the graph, or
its result would break a structural validity rule (unique IDs, exactly one primary endpoint,
no dangling references, unique visit days, no Day 0), `OperationError` is raised and no
version is created.

## Conventions

- An endpoint timepoint is a study week. Its target day is `7 x week + 1` (Week 12 = Day 85).
- Version IDs are deterministic hashes of (study, parent, branch, operation).
