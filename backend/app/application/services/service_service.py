from __future__ import annotations

from uuid import UUID, uuid4

from app.application.services.ports import ServiceRepository
from app.domain.entities.service import Service, ServiceStatus


class ServiceService:
    """Application use cases for operational services."""

    def __init__(self, repository: ServiceRepository) -> None:
        self._repository = repository

    async def list_services(self) -> list[Service]:
        return await self._repository.list()

    async def get_service(self, service_id: UUID) -> Service | None:
        return await self._repository.get_by_id(service_id=service_id)

    async def create_service(
        self,
        *,
        name: str,
        environment: str,
        status: ServiceStatus = ServiceStatus.UNKNOWN,
    ) -> Service:
        service = Service(id=uuid4(), name=name, environment=environment, status=status)
        return await self._repository.create(service)
