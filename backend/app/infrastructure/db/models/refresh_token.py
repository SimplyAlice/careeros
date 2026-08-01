"""RefreshToken model.

Stores hashed, revocable refresh tokens — the concrete mechanism behind
`docs/adr/0008-jwt-auth.md`'s "refresh tokens stored hashed with a
revocation list" design, finally implemented in Milestone 7. Only the
SHA-256 hash of the raw token is ever stored (see
`app/application/auth/auth_service.py::_hash_token`'s docstring for why
this isn't bcrypt) — the raw token itself exists only in the response
sent to the client and is never persisted.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A hashed, revocable refresh token belonging to a user."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # SHA-256 hex digest is 64 characters; unique so the same token can
    # never be issued/stored twice (astronomically unlikely with 32 bytes
    # of entropy, but the constraint costs nothing and documents the
    # invariant).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="refresh_tokens", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"RefreshToken(id={self.id!r}, user_id={self.user_id!r}, revoked={self.revoked_at is not None})"
        )
