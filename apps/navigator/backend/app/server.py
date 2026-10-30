"""Container entrypoint (S5.1): the API under ``/api``, the built SPA at ``/`` and a root ``/health``.

``app.main:app`` stays the plain API used by the Vite dev server; this module wraps it so a single image can serve
everything on port 8000. The static directory defaults to ``apps/navigator/frontend/dist`` and can be overridden with
``NAVIGATOR_STATIC_DIR``. When it is missing (API-only image, local dev) ``/`` returns a small JSON pointer instead of
failing.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response

from . import __version__
from .main import app as api
from .main import health as api_health
from .models import Health

STATIC_DIR_ENV = "NAVIGATOR_STATIC_DIR"
DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def resolve_static_dir(override: str | os.PathLike | None = None) -> Path | None:
    """The SPA build directory if it contains an ``index.html``: argument > ``NAVIGATOR_STATIC_DIR`` > default."""
    raw = override if override is not None else os.environ.get(STATIC_DIR_ENV)
    path = Path(raw).expanduser() if raw else DEFAULT_STATIC_DIR
    return path if (path / "index.html").is_file() else None


class SpaStaticFiles(StaticFiles):
    """``StaticFiles(html=True)`` that also serves ``index.html`` for unknown paths (client-side routes)."""

    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def create_app(static_dir: str | os.PathLike | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with api.router.lifespan_context(api):
            yield

    app = FastAPI(
        title="Field Force Navigator",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/api", api, name="api")

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return api_health()

    static = resolve_static_dir(static_dir)
    if static is not None:
        app.mount("/", SpaStaticFiles(directory=static, html=True), name="spa")
    else:

        @app.get("/", include_in_schema=False)
        def root() -> dict[str, str]:
            return {"message": "Field Force Navigator API (frontend build not found)", "docs": "/api/docs"}

    return app


app = create_app()
