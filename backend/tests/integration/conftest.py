"""Fixtures shared by database integration tests.

These tests exercise a **real** PostgreSQL database — not mocks, not
SQLite (SQLite can't represent the JSONB/native-enum/UUID types this
schema actually uses in production, so testing against it would validate
the wrong thing). `DATABASE_URL` is expected to point at a real,
disposable test database; see the "Commands to run locally" section in
the milestone write-up for how to provision one.

Each test gets its own engine, its own set of freshly created tables, and
its own transaction that's always rolled back — function-scoped
end-to-end. This is simpler (and a little slower) than sharing one
engine/schema across the whole test session, and deliberately so: mixing
a session-scoped async engine with pytest's per-test event loops is a
well-known source of "attached to a different loop" errors, and chasing
that complexity isn't justified at this project's current size. If test
suite runtime becomes a real problem later, session-scoped schema setup is
a legitimate optimization to revisit — not a default to start with.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# Imported for its side effect: registers all ORM models against
# Base.metadata before create_all()/drop_all() run below.
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base


@pytest.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine]:
    """A fresh engine with the schema created, for tests that need raw
    connection access rather than an ORM session (e.g. inspecting table
    names directly). Mirrors `db_session`'s setup/teardown without
    opening a session on top of it.
    """
    settings = get_settings()
    engine: AsyncEngine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """A database session backed by a fresh engine, fresh tables, and a
    transaction that's always rolled back — fully isolated per test.

    Tests call `session.flush()` rather than `session.commit()` so the
    outer transaction is never ended early; the rollback in the `finally`
    block undoes everything the test did before the tables are dropped.
    """
    settings = get_settings()
    engine: AsyncEngine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            # `join_transaction_mode="create_savepoint"` is required when a
            # Session is bound to a Connection that already has an
            # externally-managed transaction open (exactly our case here):
            # without it, a flush failure inside `session.begin_nested()`
            # (used by `SqlAlchemyJobRepository.create()` to catch
            # duplicate-key errors per-row) deactivates the *outer*
            # transaction instead of rolling back only to the SAVEPOINT —
            # found by actually running the duplicate-handling test against
            # real Postgres, not assumed.
            session_factory = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            session = session_factory()
            try:
                yield session
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
