"""Async SQLAlchemy engine and session management.

Provides a process-wide async engine and a `get_db_session` FastAPI
dependency that yields a session per request and guarantees it's closed
afterward. No repositories or models are wired in yet (Milestone 2) — this
module exists now so the dependency-injection shape is settled before
business logic lands on top of it.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async SQLAlchemy engine.

    Cached so the connection pool is created once per process, not once
    per request. `pool_pre_ping` guards against stale connections (e.g.
    after the database restarts or an idle connection is dropped by a
    managed Postgres instance) by validating a connection before use.
    """
    settings: Settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped `AsyncSession`.

    Yields a session per request, commits on success, rolls back on
    exception, and guarantees the session is closed afterward.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            if session.is_active:
                await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool.

    Called during application shutdown (see `app.main`'s lifespan handler)
    so connections are released cleanly rather than left open when the
    process exits.
    """
    await get_engine().dispose()
