"""ResumeMetadata ORM model.

Metadata only — no file content/storage. Actual resume file upload and
storage (Azure Blob Storage, per `docs/architecture/cloud-architecture.md`)
is a later milestone; this table exists now so the profile aggregate has
somewhere to record "a resume named X was uploaded at time Y" ahead of
that.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.infrastructure.db.models.profile import Profile


class ResumeMetadata(UUIDPrimaryKeyMixin, Base):
    """Metadata about a resume file, associated with a profile."""

    __tablename__ = "resume_metadata"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    # clock_timestamp(), not now() — see docs/adr/0011-clock-timestamp-for-created-at.md;
    # the same reasoning applies to any server-generated timestamp column.
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp()
    )

    profile: Mapped[Profile] = relationship(back_populates="resumes", lazy="selectin")

    def __repr__(self) -> str:
        return f"ResumeMetadata(id={self.id!r}, filename={self.filename!r})"
