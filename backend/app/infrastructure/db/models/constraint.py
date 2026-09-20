from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.planning.constraint import ConstraintType
from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.plan import PlanModel


class ConstraintModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "planning_constraints"

    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[ConstraintType] = mapped_column(
        SAEnum(
            ConstraintType,
            name="constraint_type",
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        ),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    numeric_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    plan: Mapped[PlanModel] = relationship(
        back_populates="constraints",
        lazy="selectin",
    )
