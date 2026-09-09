from uuid import UUID, uuid4

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.incident import (
    IncidentSeverity,
    IncidentStatus,
)
from app.infrastructure.db.base import Base


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    service_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity),
        nullable=False,
    )

    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus),
        nullable=False,
        default=IncidentStatus.OPEN,
    )