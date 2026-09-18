from uuid import UUID, uuid4

import pytest

from app.application.services.service_service import ServiceService
from app.domain.entities.service import Service, ServiceStatus


class FakeServiceRepository:
    def __init__(self) -> None:
        self.items: list[Service] = []

    async def list(self) -> list[Service]:
        return self.items

    async def get_by_id(self, *, service_id: UUID) -> Service | None:
        return next((item for item in self.items if item.id == service_id), None)

    async def create(self, service: Service) -> Service:
        self.items.append(service)
        return service


@pytest.mark.asyncio
async def test_create_service_uses_repository_and_domain_defaults() -> None:
    repository = FakeServiceRepository()
    service = ServiceService(repository)

    created = await service.create_service(name="payments-api", environment="production")

    assert created.name == "payments-api"
    assert created.status == ServiceStatus.UNKNOWN
    assert repository.items == [created]


@pytest.mark.asyncio
async def test_get_service_returns_none_for_unknown_id() -> None:
    service = ServiceService(FakeServiceRepository())

    assert await service.get_service(uuid4()) is None