from uuid import UUID, uuid4

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.approval import ApprovalStatus
from app.infrastructure.db.base import Base


class ApprovalModel(Base):
    __tablename__ = "approvals"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    action_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )