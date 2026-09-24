from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.constraint import ConstraintModel
    from app.infrastructure.db.models.plan_item import PlanItemModel
    from app.infrastructure.db.models.planning_context import PlanningContextModel
    from app.infrastructure.db.models.user import User


class PlanModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    intention: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    user: Mapped[User] = relationship(
        back_populates="plans",
        lazy="selectin",
    )

    context: Mapped[PlanningContextModel | None] = relationship(
        back_populates="plan",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    constraints: Mapped[list[ConstraintModel]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    items: Mapped[list[PlanItemModel]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"PlanModel(id={self.id!r}, intention={self.intention!r})"
