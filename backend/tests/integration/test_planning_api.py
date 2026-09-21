"""API-level integration tests for intelligent planning."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.main import create_app


def _prefix(resource: str) -> str:
    return f"{get_settings().api_v1_prefix}/{resource}"


@pytest.fixture
async def planning_client(db_session: AsyncSession):
    app = create_app()

    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_create_plan_from_natural_language_request(
    planning_client: AsyncClient,
) -> None:
    register_response = await planning_client.post(
        _prefix("auth/register"),
        json={
            "email": "planner@example.com",
            "password": "Sup3rSecret",
        },
    )
    assert register_response.status_code == 201

    login_response = await planning_client.post(
        _prefix("auth/login"),
        json={
            "email": "planner@example.com",
            "password": "Sup3rSecret",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = await planning_client.post(
        _prefix("planning/requests"),
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "request": (
                "I want a fun Saturday with 3 friends, "
                "R800 total, somewhere in Cape Town."
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["intention"] == (
        "I want a fun Saturday with 3 friends, "
        "R800 total, somewhere in Cape Town."
    )
    assert body["status"]
    assert body["id"]
