"""Job model.

Stores discovered job opportunities, ingested from external sources
(Adzuna, Greenhouse, Lever — wired up starting Milestone 3). `company` is
a plain string column for this milestone, not a normalized `companies`
table — matching the explicit Milestone 2 field list; normalizing into a
separate table remains a straightforward future migration if company-level
querying/aggregation becomes a real need.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.application import Application
    from app.infrastructure.db.models.generated_cover_letter import GeneratedCoverLetter
    from app.infrastructure.db.models.generated_resume import GeneratedResume
    from app.infrastructure.db.models.job_match import JobMatch


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A job posting ingested from an external source (or added manually)."""

    __tablename__ = "jobs"
    __table_args__ = (
        # This is the actual, database-enforced mechanism behind
        # "don't ingest the same posting twice" — the same guarantee
        # documented for the `jobs` table in
        # `docs/architecture/database-design.md`. Application-level dedup
        # logic (Milestone 3's ingestion service) is a courtesy for
        # avoiding unnecessary API calls; this constraint is what actually
        # holds under concurrent ingestion runs.
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
    )

    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))

    job_matches: Mapped[list[JobMatch]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Added in Milestone 6 — see docs/adr/0014-resume-cover-letter-generation.md.
    # No `delete-orphan` cascade: `generated_resumes.job_id` is nullable
    # with `ON DELETE SET NULL` — a generated resume outlives the job it
    # was tailored to (it's still a real, useful document), it just loses
    # that optional link.
    generated_resumes: Mapped[list[GeneratedResume]] = relationship(
        back_populates="job",
        lazy="selectin",
    )
    # Cover letters, unlike resumes, are always job-specific — deleting
    # the job deletes them too, matching `ON DELETE CASCADE` on
    # `generated_cover_letters.job_id`.
    generated_cover_letters: Mapped[list[GeneratedCoverLetter]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Job(id={self.id!r}, source={self.source!r}, title={self.title!r})"
