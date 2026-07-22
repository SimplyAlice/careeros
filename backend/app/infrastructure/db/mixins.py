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
    """Adds an immutable `created_at` timestamp, set by the database.

    Uses `clock_timestamp()`, not `now()`: Postgres's `now()` returns the
    *transaction's* start time — constant for every statement in the same
    transaction — while `clock_timestamp()` returns the actual wall-clock
    time at statement execution. Since a single batch job-ingestion run
    (Milestone 3) can insert many rows in one transaction, `now()` would
    give them all an identical `created_at`, breaking the newest-first
    ordering `SqlAlchemyJobRepository.list_jobs()` depends on — found by
    actually running the pagination test against real Postgres.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        nullable=False,
    )


class TimestampMixin(CreatedAtMixin):
    """Adds `created_at` and a `updated_at` maintained by the database on every update.

    Same `clock_timestamp()` reasoning as `CreatedAtMixin` applies to
    `updated_at`'s `onupdate` value.
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
        nullable=False,
    )
