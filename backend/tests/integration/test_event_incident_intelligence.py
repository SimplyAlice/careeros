from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.domain.entities.incident import Incident, IncidentSeverity, IncidentStatus
from app.domain.entities.service import Service, ServiceStatus
from app.infrastructure.db.repositories.operations_repositories import (
    SqlAlchemyEventRepository,
    SqlAlchemyIncidentRepository,
)
from app.infrastructure.db.repositories.service_repository import SqlAlchemyServiceRepository


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


async def _create_service(db_session: AsyncSession) -> UUID:
    service = Service(uuid4(), "payments-api", "production", ServiceStatus.HEALTHY)
    await SqlAlchemyServiceRepository(db_session).create(service)
    return service.id


@pytest.mark.asyncio
async def test_problematic_event_creates_and_links_incident(
    database_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service_id = await _create_service(db_session)

    response = await database_client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": "error",
            "severity": "critical",
            "message": "Payment API returned HTTP 500.",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["incident_id"] is not None
    assert body["evaluation_reason"] == "critical event severity"

    incidents_response = await database_client.get("/api/v1/incidents")
    assert incidents_response.status_code == 200
    incident = incidents_response.json()[0]
    assert incident["id"] == body["incident_id"]
    assert incident["service_id"] == str(service_id)
    assert incident["severity"] == "critical"
    assert incident["detection_reason"] == "critical event severity"

    persisted_event = await SqlAlchemyEventRepository(db_session).list()
    assert persisted_event[0].incident_id == UUID(body["incident_id"])


@pytest.mark.asyncio
async def test_second_problematic_event_reuses_and_escalates_incident(
    database_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service_id = await _create_service(db_session)
    first = await database_client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": "alert",
            "severity": "warning",
            "message": "Latency alert.",
        },
    )
    second = await database_client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": "error",
            "severity": "critical",
            "message": "Requests are failing.",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["incident_id"] == second.json()["incident_id"]
    assert (await database_client.get("/api/v1/incidents")).json()[0]["severity"] == "critical"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "severity"),
    [("health_check", "warning"), ("deployment", "info")],
)
async def test_non_problematic_event_does_not_create_incident(
    database_client: AsyncClient,
    db_session: AsyncSession,
    event_type: str,
    severity: str,
) -> None:
    service_id = await _create_service(db_session)

    response = await database_client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": event_type,
            "severity": severity,
            "message": "Routine operational signal.",
        },
    )

    assert response.status_code == 201
    assert response.json()["incident_id"] is None
    assert response.json()["evaluation_reason"] == "event does not meet incident detection rules"
    assert (await database_client.get("/api/v1/incidents")).json() == []


@pytest.mark.asyncio
async def test_incident_repository_finds_only_active_incidents(db_session: AsyncSession) -> None:
    service_id = await _create_service(db_session)
    repository = SqlAlchemyIncidentRepository(db_session)
    resolved = Incident(uuid4(), service_id, "Resolved", IncidentSeverity.HIGH, IncidentStatus.RESOLVED)
    active = Incident(uuid4(), service_id, "Active", IncidentSeverity.MEDIUM, IncidentStatus.INVESTIGATING)

    await repository.create(resolved)
    await repository.create(active)

    found = await repository.get_active_for_service(service_id=service_id)

    assert found is not None
    assert found.id == active.id
