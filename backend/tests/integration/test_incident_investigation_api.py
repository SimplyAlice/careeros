from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session


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


async def _create_service_and_events(client: AsyncClient) -> tuple[UUID, UUID]:
    service = await client.post(
        "/api/v1/services",
        json={"name": "payments-api", "environment": "production", "status": "degraded"},
    )
    service_id = UUID(service.json()["id"])
    first = await client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": "alert",
            "severity": "warning",
            "message": "Latency alert detected.",
        },
    )
    await client.post(
        "/api/v1/events",
        json={
            "service_id": str(service_id),
            "event_type": "error",
            "severity": "critical",
            "message": "Payment API returned HTTP 500.",
        },
    )
    return service_id, UUID(first.json()["incident_id"])


@pytest.mark.asyncio
async def test_investigation_returns_persisted_evidence_and_findings(database_client: AsyncClient) -> None:
    service_id, incident_id = await _create_service_and_events(database_client)

    response = await database_client.get(f"/api/v1/incidents/{incident_id}/investigation")

    assert response.status_code == 200
    body = response.json()
    assert body["incident"]["id"] == str(incident_id)
    assert body["service"]["id"] == str(service_id)
    assert body["service"]["status"] == "degraded"
    assert body["event_count"] == 2
    assert [event["sequence"] for event in body["events"]] == [1, 2]
    assert body["ordering"] == {"basis": "event_id", "chronology_available": False}
    assert "At least one event has critical severity." in body["findings"]
    assert "The event set contains an error or alert signal." in body["findings"]
    assert "The event set contains multiple severity levels." in body["findings"]


@pytest.mark.asyncio
async def test_investigation_with_no_events_returns_empty_evidence(database_client: AsyncClient) -> None:
    service = await database_client.post(
        "/api/v1/services",
        json={"name": "quiet-api", "environment": "staging", "status": "healthy"},
    )
    incident = await database_client.post(
        "/api/v1/incidents",
        json={
            "service_id": service.json()["id"],
            "title": "Manual review",
            "severity": "low",
        },
    )

    response = await database_client.get(f"/api/v1/incidents/{incident.json()['id']}/investigation")

    assert response.status_code == 200
    assert response.json()["events"] == []
    assert response.json()["event_count"] == 0
    assert "No associated event evidence is available." in response.json()["findings"]


@pytest.mark.asyncio
async def test_unknown_incident_returns_404(database_client: AsyncClient) -> None:
    response = await database_client.get(f"/api/v1/incidents/{UUID(int=0)}/investigation")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_investigation_does_not_mutate_persisted_data(database_client: AsyncClient) -> None:
    _, incident_id = await _create_service_and_events(database_client)
    before = await database_client.get("/api/v1/events")
    before_incidents = await database_client.get("/api/v1/incidents")

    response = await database_client.get(f"/api/v1/incidents/{incident_id}/investigation")

    assert response.status_code == 200
    assert (await database_client.get("/api/v1/events")).json() == before.json()
    assert (await database_client.get("/api/v1/incidents")).json() == before_incidents.json()
