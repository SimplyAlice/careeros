"""Alembic migration environment.

Configured for async SQLAlchemy (matching `app.infrastructure.db.session`)
and wired to read the database URL from application `Settings` rather than
a hardcoded value in `alembic.ini`, so migrations always target whichever
database the running environment is configured for.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings
from app.infrastructure.db.base import Base

# Imported for its side effect: every model module imports and registers
# itself against `Base.metadata` when this package is imported. Without
# this import, `Base.metadata` would be empty here (no model module would
# have been loaded yet) and `--autogenerate` would see no tables at all.
from app.infrastructure.db import models  # noqa: F401

# Alembic Config object, providing access to values in alembic.ini.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a live DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live async database connection."""
    connectable: AsyncEngine = create_async_engine(settings.database_url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
