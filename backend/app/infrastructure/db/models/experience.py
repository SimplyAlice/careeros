"""Experience ORM model."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.profile import Profile


class Experience(UUIDPrimaryKeyMixin, Base):
    """A single work-experience entry belonging to a profile."""

    __tablename__ = "experience"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    currently_working: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(Text)

    profile: Mapped[Profile] = relationship(back_populates="experience_entries", lazy="selectin")

    def __repr__(self) -> str:
        return f"Experience(id={self.id!r}, company={self.company!r}, title={self.title!r})"
