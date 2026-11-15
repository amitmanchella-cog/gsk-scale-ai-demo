from __future__ import annotations

import pytest

from csd_core.adapters.memory_store import InMemoryVersionStore
from csd_core.application.study_service import StudyService
from csd_core.domain.versioning import Version
from csd_core.reference.asthma import REFERENCE_STUDY_ID, reference_study


@pytest.fixture
def service() -> StudyService:
    return StudyService(InMemoryVersionStore())


@pytest.fixture
def root(service: StudyService) -> Version:
    return service.create_study(REFERENCE_STUDY_ID, reference_study())
