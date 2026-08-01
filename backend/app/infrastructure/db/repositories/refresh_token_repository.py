"""RefreshToken repository.

Implements `RefreshTokenRepository` (`app/application/auth/ports.py`)
against SQLAlchemy.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import RefreshToken


class SqlAlchemyRefreshTokenRepository:
    """SQLAlchemy-backed implementation of the `RefreshTokenRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        record = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_active(self, *, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, *, token_hash: str) -> None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            await self._session.flush()
