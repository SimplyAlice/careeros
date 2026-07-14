"""SQLAlchemy declarative base.

A single shared `Base` that every ORM model (added starting Milestone 2)
inherits from, so Alembic's autogenerate can discover all models via
`Base.metadata` regardless of which module they're defined in.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Without an explicit naming convention, SQLAlchemy/Postgres auto-generate
# constraint names (e.g. a random suffix for unique constraints), which
# makes Alembic autogenerate diffs noisy and non-reproducible across
# environments. Fixing the convention now — before the first migration —
# means every constraint has a deterministic, greppable name
# (e.g. `uq_applications_user_id`) from day one.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
