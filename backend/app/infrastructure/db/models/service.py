from uuid import UUID, uuid4

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.service import ServiceStatus
from app.infrastructure.db.base import Base


class ServiceModel(Base):
    __tablename__ = "services"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    environment: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus),
        nullable=False,
        default=ServiceStatus.UNKNOWN,
    )
