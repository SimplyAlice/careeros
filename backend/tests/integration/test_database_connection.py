"""Verifies basic database connectivity and that every model's table exists.

This is the most fundamental integration guarantee: if this file fails,
nothing else in `tests/integration/` can be trusted either.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.infrastructure.db.base import Base

EXPECTED_TABLES = {
    "users",
    "candidate_profiles",
    "resumes",
    "jobs",
    "job_matches",
    "applications",
}


@pytest.mark.asyncio
async def test_database_connection_works(db_session: AsyncSession) -> None:
    """A trivial round-trip query confirms the app can actually reach Postgres."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_all_model_tables_exist(db_engine: AsyncEngine) -> None:
    """Every table declared on `Base.metadata` should exist in the database
    after the schema-setup fixture has run — i.e. the ORM models and the
    live schema genuinely agree with each other.
    """

    def _get_table_names(sync_conn: object) -> set[str]:
        return set(inspect(sync_conn).get_table_names())

    async with db_engine.connect() as conn:
        table_names = await conn.run_sync(_get_table_names)

    assert EXPECTED_TABLES.issubset(table_names)
    # Every table registered on Base.metadata is also actually present —
    # catches the opposite mistake (a model defined but never migrated).
    assert set(Base.metadata.tables.keys()).issubset(table_names)
