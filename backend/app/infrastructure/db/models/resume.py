"""Resume model.

Stores resumes associated with a user. One `User` can have multiple
`Resume` rows (no uniqueness constraint on `user_id`).

Note: this is intentionally a single flat table for Milestone 2, matching
the explicit field list given for this milestone — simpler than the
`resumes` + immutable `resume_versions` lineage originally sketched in
`docs/architecture/database-design.md`. That richer versioning model
remains a valid future evolution (Milestone 5, when AI-generated tailored
resumes need per-job version history) and can be introduced as an
additive migration without breaking this table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.user import User


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A resume document belonging to a user."""

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    file_url: Mapped[str | None] = mapped_column(String(2048))

    user: Mapped[User] = relationship(back_populates="resumes", lazy="selectin")

    def __repr__(self) -> str:
        return f"Resume(id={self.id!r}, user_id={self.user_id!r}, title={self.title!r})"
