"""Integration tests for `SqlAlchemyRefreshTokenRepository` against real PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository


async def _seeded_user(session: AsyncSession):
    user = await SqlAlchemyUserRepository(session).create(email="ada@example.com", password_hash="hash")
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_create_then_get_active_round_trips(db_session: AsyncSession) -> None:
    user = await _seeded_user(db_session)
    repository = SqlAlchemyRefreshTokenRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(days=30)

    await repository.create(user_id=user.id, token_hash="hash-abc", expires_at=expires_at)
    await db_session.flush()

    found = await repository.get_active(token_hash="hash-abc")

    assert found is not None
    assert found.user_id == user.id


@pytest.mark.asyncio
async def test_get_active_returns_none_for_unknown_hash(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRefreshTokenRepository(db_session)

    found = await repository.get_active(token_hash="never-created")

    assert found is None


@pytest.mark.asyncio
async def test_get_active_returns_none_for_an_expired_token(db_session: AsyncSession) -> None:
    user = await _seeded_user(db_session)
    repository = SqlAlchemyRefreshTokenRepository(db_session)
    already_expired = datetime.now(UTC) - timedelta(minutes=1)

    await repository.create(user_id=user.id, token_hash="expired-hash", expires_at=already_expired)
    await db_session.flush()

    found = await repository.get_active(token_hash="expired-hash")

    assert found is None


@pytest.mark.asyncio
async def test_revoke_then_get_active_returns_none(db_session: AsyncSession) -> None:
    user = await _seeded_user(db_session)
    repository = SqlAlchemyRefreshTokenRepository(db_session)
    expires_at = datetime.now(UTC) + timedelta(days=30)
    await repository.create(user_id=user.id, token_hash="hash-to-revoke", expires_at=expires_at)
    await db_session.flush()

    await repository.revoke(token_hash="hash-to-revoke")
    await db_session.flush()

    found = await repository.get_active(token_hash="hash-to-revoke")
    assert found is None


@pytest.mark.asyncio
async def test_revoke_is_idempotent_for_an_unknown_hash(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRefreshTokenRepository(db_session)

    await repository.revoke(token_hash="never-created")  # should not raise
