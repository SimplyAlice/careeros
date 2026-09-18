from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.service import Service, ServiceStatus
from app.infrastructure.db.models import ServiceModel


class SqlAlchemyServiceRepository:
    """SQLAlchemy-backed Service repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[Service]:
        result = await self._session.execute(select(ServiceModel).order_by(ServiceModel.name, ServiceModel.id))
        return [_to_entity(row) for row in result.scalars().all()]

    async def get_by_id(self, *, service_id: UUID) -> Service | None:
        row = await self._session.get(ServiceModel, service_id)
        return _to_entity(row) if row is not None else None

    async def create(self, service: Service) -> Service:
        row = ServiceModel(
            id=service.id,
            name=service.name,
            environment=service.environment,
            status=service.status,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return _to_entity(row)


def _to_entity(row: ServiceModel) -> Service:
    return Service(
        id=row.id,
        name=row.name,
        environment=row.environment,
        status=ServiceStatus(row.status),
    )
