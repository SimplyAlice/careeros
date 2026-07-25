"""JobMatch model.

Stores AI-generated matching information between a profile and a job
(populated by Milestone 5's scoring engine). Deliberately has only
`created_at`, not a full timestamp pair — a match is a point-in-time
scoring snapshot, not a mutable record; re-scoring produces a new row
rather than updating an old one, which also means score history over time
is naturally queryable (see `docs/architecture/database-design.md` §3).

`profile_id` and the now-nullable `user_id` reflect a real architectural
decision made in Milestone 5 — see `docs/adr/0013-score-against-profile-not-user.md`
for the full reasoning: this table originally referenced `users` (a
multi-user concept with no registration flow yet), and scoring needed to
work against the actual single local profile Milestone 4 introduced.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.job import Job
    from app.infrastructure.db.models.profile import Profile
    from app.infrastructure.db.models.user import User


class JobMatch(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An AI-computed compatibility score between a profile and a job."""

    __tablename__ = "job_matches"
    __table_args__ = (
        # A score is defined as 0-100 throughout the architecture docs
        # (see FR-4 in `docs/architecture/system-design.md`) — enforcing
        # the range at the database level catches a bad AI-provider
        # response or a unit-conversion bug (e.g. writing a 0.0-1.0
        # fraction into a 0-100 column) before it silently corrupts
        # analytics built on top of this table.
        CheckConstraint("match_score >= 0 AND match_score <= 100", name="score_range"),
    )

    # Nullable: no registration flow exists yet to populate a real `users`
    # row (the same situation `candidate_profiles` was in — see
    # docs/adr/0012-profile-management.md). Kept, not dropped, so the
    # column is ready to become the real per-user reference once auth
    # lands, without another schema change to reintroduce it.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    # The FK actually populated by Milestone 5's scoring service — see
    # docs/adr/0013-score-against-profile-not-user.md.
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # NUMERIC (not FLOAT) so score comparisons/aggregations in analytics
    # queries (Milestone 13) aren't subject to floating-point rounding.
    match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    # JSONB string-array columns — the same choice `CandidateProfile.skills`
    # (Milestone 2) made for the same kind of data (a short list of skill
    # names), added here rather than folding them into `reasoning` as
    # unstructured text, which a frontend can't render as distinct
    # chips/tags without re-parsing free text.
    matched_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    missing_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    user: Mapped[User | None] = relationship(back_populates="job_matches", lazy="selectin")
    profile: Mapped[Profile | None] = relationship(back_populates="job_matches", lazy="selectin")
    job: Mapped[Job] = relationship(back_populates="job_matches", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"JobMatch(id={self.id!r}, profile_id={self.profile_id!r}, "
            f"job_id={self.job_id!r}, score={self.match_score!r})"
        )
