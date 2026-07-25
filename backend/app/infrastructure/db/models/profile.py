"""Profile ORM model.

A deliberately standalone table — not linked to `users`/`candidate_profiles`
(Milestone 2). See `docs/adr/0012-profile-management.md` for the full
reasoning; in short: this is a temporary, single-tenant profile store for
the pre-authentication phase of the product, reconciled with the
multi-user `users`/`candidate_profiles` design once JWT auth lands.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.profile import RemotePreference
from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.education import Education
    from app.infrastructure.db.models.experience import Experience
    from app.infrastructure.db.models.job_match import JobMatch
    from app.infrastructure.db.models.resume_metadata import ResumeMetadata
    from app.infrastructure.db.models.skill import Skill


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The job seeker's profile — a singleton table.

    Enforced via `ix_profiles_singleton`: a unique index on the constant
    expression `(true)`, which is identical for every row and therefore
    rejects any insert beyond the first — the standard Postgres technique
    for a "this table may have at most one row" constraint. (Postgres
    requires the extra grouping parens — a bare `true` isn't parsed as an
    index expression — found by actually running the migration, not
    assumed.) An application-level check (`ProfileService.create_profile`
    calling `repository.get()` first) avoids the wasted round trip in the
    common case; this index is what actually holds under a race, matching
    the two-layers-of-dedup pattern already used for jobs (Milestone 3).
    """

    __tablename__ = "profiles"
    __table_args__ = (Index("ix_profiles_singleton", text("(true)"), unique=True),)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(255))
    headline: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    preferred_job_title: Mapped[str | None] = mapped_column(String(255))
    preferred_location: Mapped[str | None] = mapped_column(String(255))
    salary_expectation: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    remote_preference: Mapped[RemotePreference] = mapped_column(
        SAEnum(
            RemotePreference,
            name="remote_preference",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=RemotePreference.FLEXIBLE,
        server_default=RemotePreference.FLEXIBLE.value,
    )

    skills: Mapped[list[Skill]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    experience_entries: Mapped[list[Experience]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    education_entries: Mapped[list[Education]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    resumes: Mapped[list[ResumeMetadata]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    # Added in Milestone 5 — see docs/adr/0013-score-against-profile-not-user.md.
    # `cascade="all, delete-orphan"` mirrors the DB-level `ON DELETE
    # CASCADE` on `job_matches.profile_id`: deleting the profile deletes
    # its scoring history too, consistent with matches being a snapshot
    # *about* a profile, not an independent record worth orphaning.
    job_matches: Mapped[list[JobMatch]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Profile(id={self.id!r}, email={self.email!r})"
