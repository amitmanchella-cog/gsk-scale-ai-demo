"""ASGI entry point: ``uvicorn csd_api.main:app``."""

from csd_api.app import create_app

app = create_app()
