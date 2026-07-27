"""GeneratedResume model.

Stores a versioned, AI-tailored resume: the AI-generated summary/skill
emphasis (`professional_summary`, `emphasized_skills`) plus a pointer to
the rendered PDF (`file_path`). Deliberately has only `created_at` — like
`JobMatch` (Milestone 5), a generated resume is a point-in-time snapshot;
regenerating produces a new row, not an update to an old one, so version
history is naturally queryable.

Distinct from `Resume` (Milestone 2, unused, tied to `users`) and
`ResumeMetadata` (Milestone 4, upload metadata only, no content) — see
`docs/adr/0014-resume-cover-letter-generation.md` for why this is a new
table rather than reusing either.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.job import Job
    from app.infrastructure.db.models.profile import Profile


class GeneratedResume(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A versioned, AI-tailored resume generated for the profile."""

    __tablename__ = "generated_resumes"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Nullable: a resume can be generated generically (no target job) or
    # tailored to a specific one.
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    professional_summary: Mapped[str] = mapped_column(Text, nullable=False)
    emphasized_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="generated_resumes", lazy="selectin")
    job: Mapped[Job | None] = relationship(back_populates="generated_resumes", lazy="selectin")

    def __repr__(self) -> str:
        return f"GeneratedResume(id={self.id!r}, profile_id={self.profile_id!r}, job_id={self.job_id!r})"
