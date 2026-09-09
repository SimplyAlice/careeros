from uuid import UUID, uuid4

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.action import ActionStatus, ActionType
from app.infrastructure.db.base import Base


class ActionModel(Base):
    __tablename__ = "actions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    service_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )

    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus),
        nullable=False,
        default=ActionStatus.PENDING,
    )