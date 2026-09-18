from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.service import Service, ServiceStatus
from app.infrastructure.db.repositories.service_repository import SqlAlchemyServiceRepository


@pytest.mark.asyncio
async def test_service_repository_create_list_and_get(db_session: AsyncSession) -> None:
    repository = SqlAlchemyServiceRepository(db_session)
    service = Service(
        id=uuid4(),
        name="payments-api",
        environment="production",
        status=ServiceStatus.HEALTHY,
    )

    created = await repository.create(service)
    services = await repository.list()
    fetched = await repository.get_by_id(service_id=service.id)

    assert created == service
    assert services == [service]
    assert fetched == service


@pytest.mark.asyncio
async def test_service_repository_list_is_empty(db_session: AsyncSession) -> None:
    repository = SqlAlchemyServiceRepository(db_session)

    assert await repository.list() == []
