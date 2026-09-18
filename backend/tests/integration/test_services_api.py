from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.domain.entities.service import Service, ServiceStatus
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


@pytest.mark.asyncio
async def test_list_services_returns_empty_database(database_client: AsyncClient) -> None:
    response = await database_client.get("/api/v1/services")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_services_returns_persisted_service(
    database_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service_id: UUID = uuid4()
    await SqlAlchemyServiceRepository(db_session).create(
        Service(
            id=service_id,
            name="payments-api",
            environment="production",
            status=ServiceStatus.HEALTHY,
        )
    )

    response = await database_client.get("/api/v1/services")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(service_id),
            "name": "payments-api",
            "environment": "production",
            "status": "healthy",
        }
    ]


@pytest.mark.asyncio
async def test_create_service_persists_and_returns_service(database_client: AsyncClient) -> None:
    response = await database_client.post(
        "/api/v1/services",
        json={"name": "orders-api", "environment": "staging", "status": "degraded"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "orders-api"
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_create_service_rejects_empty_name(database_client: AsyncClient) -> None:
    response = await database_client.post(
        "/api/v1/services",
        json={"name": "", "environment": "production"},
    )

    assert response.status_code == 422
