"""Integration tests for `SqlAlchemyUserRepository` against real PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.errors import UserAlreadyExistsError
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository


@pytest.mark.asyncio
async def test_create_then_get_by_email_round_trips(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)

    created = await repository.create(email="ada@example.com", password_hash="hashed-value")
    await db_session.flush()

    found = await repository.get_by_email(email="ada@example.com")

    assert found is not None
    assert found.id == created.id
    assert found.password_hash == "hashed-value"


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_not_found(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)

    found = await repository.get_by_email(email="nobody@example.com")

    assert found is None


@pytest.mark.asyncio
async def test_get_by_id_round_trips(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)
    created = await repository.create(email="ada@example.com", password_hash="hashed-value")
    await db_session.flush()

    found = await repository.get_by_id(user_id=created.id)

    assert found is not None
    assert found.email == "ada@example.com"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)

    found = await repository.get_by_id(user_id=uuid.uuid4())

    assert found is None


@pytest.mark.asyncio
async def test_create_duplicate_email_raises_and_session_remains_usable(db_session: AsyncSession) -> None:
    repository = SqlAlchemyUserRepository(db_session)
    await repository.create(email="ada@example.com", password_hash="hash-one")
    await db_session.flush()

    with pytest.raises(UserAlreadyExistsError):
        await repository.create(email="ada@example.com", password_hash="hash-two")

    # The session must remain usable after the caught duplicate — proves
    # the SAVEPOINT-scoped create() didn't leave the session deactivated,
    # the same property already proven for jobs/profiles in Milestones 3-4.
    second_user = await repository.create(email="someone-else@example.com", password_hash="hash-three")
    await db_session.flush()
    found = await repository.get_by_email(email="someone-else@example.com")
    assert found is not None
    assert found.id == second_user.id
