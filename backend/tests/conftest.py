"""Shared pytest fixtures.

Environment variables for the `testing` environment are set via
`pytest-env` in `pyproject.toml` *before* any application module is
imported, so `Settings` picks them up naturally the same way it would from
a real `.env` file — no monkeypatching of settings objects required.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app() -> FastAPI:
    """A fresh FastAPI app instance for each test.

    Built via the `create_app()` factory (see `app.main`) rather than
    importing the module-level `app` directly, keeping each test's app
    instance isolated.
    """
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """An async HTTP client wired directly to the app (no real network call)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
