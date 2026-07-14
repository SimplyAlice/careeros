"""CandidateProfile model.

Stores the user's professional profile — the source material later used
to score jobs and tailor resumes (Milestones 4–5). One `User` has at most
one `CandidateProfile`, enforced by the unique constraint on `user_id`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.user import User


class CandidateProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's professional profile — the master source resumes are tailored from."""

    __tablename__ = "candidate_profiles"

    # unique=True is what makes this a genuine one-to-one relationship at
    # the database level, not just a convention followed in application
    # code — a second profile row for the same user is rejected by Postgres.
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    professional_summary: Mapped[str | None] = mapped_column(Text)

    # JSONB (not separate relational tables) is a deliberate choice here:
    # skills/experience/education are free-form, iterate quickly, and are
    # read/written as a whole document (the AI tailoring services in
    # Milestone 4/5 consume the entire profile at once) rather than
    # queried field-by-field — the case JSONB is meant for, per
    # `docs/architecture/database-design.md` §3. `default=list` (Python
    # side) plus a matching `server_default` (DB side) means the column is
    # never NULL, even for a row inserted outside the ORM.
    skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    experience: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    education: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    user: Mapped[User] = relationship(back_populates="candidate_profile", lazy="selectin")

    def __repr__(self) -> str:
        return f"CandidateProfile(id={self.id!r}, user_id={self.user_id!r})"
