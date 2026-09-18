from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.event import EventSeverity, EventType
from app.infrastructure.db.base import Base


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    service_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )

    incident_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("incidents.id"),
        nullable=True,
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType),
        nullable=False,
    )

    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    evaluation_reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
