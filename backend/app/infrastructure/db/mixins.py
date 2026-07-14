"""Reusable ORM column mixins.

Every model needs a UUID primary key; most need `created_at`/`updated_at`.
Factoring these into mixins keeps that repetition out of six near-identical
model definitions and guarantees the same column types/defaults are used
everywhere (a single-column-name typo across a hand-copied "created_at"
in six files is exactly the kind of thing this prevents).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key, generated application-side.

    Generated in Python (`default=uuid.uuid4`) rather than relying on a
    Postgres server-side default (`gen_random_uuid()`) so the ID is known
    immediately after `session.add()`, before a flush — useful for
    building related objects in the same unit of work without a round
    trip to the database first.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class CreatedAtMixin:
    """Adds an immutable `created_at` timestamp, set by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin):
    """Adds `created_at` and a `updated_at` maintained by the database on every update.

    Using `server_default` / `server_onupdate` (database-side `now()`)
    rather than Python-side `datetime.utcnow()` means the timestamp is
    correct even for updates made outside the application (e.g. a manual
    `UPDATE` during a migration or a support fix), and avoids clock-skew
    issues between application servers.
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
