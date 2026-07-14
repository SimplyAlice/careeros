"""Tests for basic application startup and root endpoint behavior."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import get_settings


def test_app_factory_builds_without_error(app: FastAPI) -> None:
    """`create_app()` should assemble a fully-configured FastAPI instance
    without raising — this is the most basic possible startup guarantee,
    and it's the test that would catch a broken import chain or a
    misconfigured dependency before it ever reaches a running container.
    """
    assert isinstance(app, FastAPI)
    settings = get_settings()
    assert app.title == settings.project_name


@pytest.mark.asyncio
async def test_root_endpoint_returns_service_info(client: AsyncClient) -> None:
    settings = get_settings()

    response = await client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == settings.project_name
    assert body["version"] == settings.version


@pytest.mark.asyncio
async def test_docs_available_outside_production(client: AsyncClient) -> None:
    """Interactive API docs should be reachable in the testing environment
    (see `Settings.docs_enabled` — disabled only in production).
    """
    response = await client.get("/docs")

    assert response.status_code == 200
