from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.infrastructure.db.models import ActionModel, ApprovalModel


@pytest.fixture
async def database_client(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    async def override_db_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


async def _create_incident(client: AsyncClient) -> tuple[UUID, UUID]:
    service = await client.post(
        "/api/v1/services",
        json={"name": "payments-api", "environment": "production", "status": "degraded"},
    )
    service_id = UUID(service.json()["id"])
    event = await client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": "error",
            "severity": "critical",
            "message": "Payment API returned HTTP 500.",
        },
    )
    return service_id, UUID(event.json()["incident_id"])


@pytest.mark.asyncio
async def test_recommendation_uses_postgres_evidence_without_creating_rows(
    database_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, incident_id = await _create_incident(database_client)
    actions_before = await db_session.scalar(select(func.count()).select_from(ActionModel))
    approvals_before = await db_session.scalar(select(func.count()).select_from(ApprovalModel))

    first = await database_client.get(f"/api/v1/incidents/{incident_id}/recommendation")
    second = await database_client.get(f"/api/v1/incidents/{incident_id}/recommendation")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["recommendation"]["action_type"] == "restart_service"
    assert first.json()["recommendation"]["requires_approval"] is True
    assert first.json()["evidence"]["critical_event_present"] is True
    assert first.json()["evidence"]["service_status"] == "degraded"
    assert first.json()["investigation_ordering"] == {
        "basis": "event_id",
        "chronology_available": False,
    }

    assert await db_session.scalar(select(func.count()).select_from(ActionModel)) == actions_before
    assert await db_session.scalar(select(func.count()).select_from(ApprovalModel)) == approvals_before


@pytest.mark.asyncio
async def test_unknown_incident_recommendation_returns_404(database_client: AsyncClient) -> None:
    response = await database_client.get(f"/api/v1/incidents/{UUID(int=0)}/recommendation")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_no_matching_evidence_returns_null_recommendation(database_client: AsyncClient) -> None:
    service = await database_client.post(
        "/api/v1/services",
        json={"name": "healthy-api", "environment": "production", "status": "healthy"},
    )
    incident = await database_client.post(
        "/api/v1/incidents",
        json={
            "service_id": service.json()["id"],
            "title": "Resolved review",
            "severity": "low",
            "status": "resolved",
        },
    )

    response = await database_client.get(f"/api/v1/incidents/{incident.json()['id']}/recommendation")

    assert response.status_code == 200
    assert response.json()["recommendation"] is None
