"""User model.

Represents the CareerOS account owner. This milestone only defines the
identity/timestamp shape of the table — password hashing and auth fields
land when JWT authentication is implemented (a later milestone), per the
Milestone 2 scope boundary (no auth yet).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.application import Application
    from app.infrastructure.db.models.candidate_profile import CandidateProfile
    from app.infrastructure.db.models.job_match import JobMatch
    from app.infrastructure.db.models.resume import Resume


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A CareerOS account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)

    # `lazy="selectin"` on every relationship here (and throughout the
    # other models in this package) is a deliberate, project-wide default:
    # SQLAlchemy's default lazy-loading behavior triggers implicit I/O when
    # an unloaded relationship attribute is accessed, which raises
    # `MissingGreenlet` under asyncio rather than silently working the way
    # it does under a sync engine. `selectin` issues a second, explicit
    # SELECT eagerly and is the standard-recommended default for async
    # SQLAlchemy. Call sites that need different loading behavior (e.g. a
    # list endpoint that shouldn't eagerly load every relationship) can
    # override this per-query later.
    candidate_profile: Mapped[CandidateProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    job_matches: Mapped[list[JobMatch]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"
