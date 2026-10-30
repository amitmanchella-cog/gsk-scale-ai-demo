"""Load ``apps/navigator/backend/app`` for the tests.

``services/supply_api`` also ships a top-level package called ``app``; when the whole repo runs in one pytest
process (``pytest`` from the repo root) the two would collide in ``sys.modules``. The backend package only uses
relative imports, so we load it here under the unique alias ``navigator_app`` and tests import from that.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ALIAS = "navigator_app"


def _load_backend_package(alias: str = PACKAGE_ALIAS):
    if alias in sys.modules:
        return sys.modules[alias]
    package_dir = BACKEND_ROOT / "app"
    spec = importlib.util.spec_from_file_location(
        alias, package_dir / "__init__.py", submodule_search_locations=[str(package_dir)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


_load_backend_package()

from navigator_app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
