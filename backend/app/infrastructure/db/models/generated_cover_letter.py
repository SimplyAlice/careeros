"""GeneratedCoverLetter model.

Stores a versioned, AI-generated cover letter for a specific job (a
cover letter, unlike a resume, is always job-specific — see
`docs/architecture/ai-architecture.md`). Deliberately has only
`created_at`, matching `GeneratedResume` and `JobMatch`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.job import Job
    from app.infrastructure.db.models.profile import Profile


class GeneratedCoverLetter(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A versioned, AI-generated cover letter for a specific job."""

    __tablename__ = "generated_cover_letters"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="generated_cover_letters", lazy="selectin")
    job: Mapped[Job] = relationship(back_populates="generated_cover_letters", lazy="selectin")

    def __repr__(self) -> str:
        return f"GeneratedCoverLetter(id={self.id!r}, profile_id={self.profile_id!r}, job_id={self.job_id!r})"
