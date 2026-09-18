from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.entities.service import Service


class ServiceRepository(Protocol):
    async def list(self) -> list[Service]:
        """Return all services in stable name order."""
        ...

    async def get_by_id(self, *, service_id: UUID) -> Service | None:
        """Return a service by ID, or None when it does not exist."""
        ...

    async def create(self, service: Service) -> Service:
        """Persist and return a service."""
        ...
