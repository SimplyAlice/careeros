"""Skill ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.profile import Profile


class Skill(UUIDPrimaryKeyMixin, Base):
    """A single named skill belonging to a profile.

    No timestamps — per the Milestone 4 field list, a skill is just an id,
    a profile reference, and a name.
    """

    __tablename__ = "skills"
    __table_args__ = (
        # Database-level backstop for the domain-level duplicate check in
        # `Profile.replace_skills` — the same two-layer pattern used for
        # job dedup in Milestone 3.
        UniqueConstraint("profile_id", "name", name="uq_skills_profile_id_name"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="skills", lazy="selectin")

    def __repr__(self) -> str:
        return f"Skill(id={self.id!r}, name={self.name!r})"
