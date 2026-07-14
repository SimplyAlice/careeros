"""Application model.

Tracks a user's job applications through their lifecycle. This is the
central tracking entity referenced throughout `docs/architecture/database-design.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.job import Job
    from app.infrastructure.db.models.user import User


class ApplicationStatus(StrEnum):
    """The lifecycle states an application moves through.

    Modeled as a native Postgres enum (via SQLAlchemy's `Enum` type
    below), not a plain string column — an invalid status is rejected by
    the database itself, not just by application-layer validation that a
    future direct-SQL fix or a bug could bypass.
    """

    SAVED = "saved"
    REVIEWING = "reviewing"
    READY = "ready"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tracked application from a user to a job."""

    __tablename__ = "applications"
    __table_args__ = (
        # The database-enforced guarantee behind "don't apply to the same
        # job twice" (FR-14 in `docs/architecture/system-design.md`) — this
        # holds even under concurrent requests, which an application-layer
        # "check then insert" cannot guarantee on its own.
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_id_job_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(
            ApplicationStatus,
            name="application_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ApplicationStatus.SAVED,
        server_default=ApplicationStatus.SAVED.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="applications", lazy="selectin")
    job: Mapped[Job] = relationship(back_populates="applications", lazy="selectin")

    def __repr__(self) -> str:
        return f"Application(id={self.id!r}, user_id={self.user_id!r}, job_id={self.job_id!r}, status={self.status!r})"
