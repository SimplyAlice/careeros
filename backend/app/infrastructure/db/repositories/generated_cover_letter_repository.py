"""GeneratedCoverLetter repository.

Implements `GeneratedCoverLetterRepository` (`app/application/documents/ports.py`)
against SQLAlchemy, mirroring `SqlAlchemyGeneratedResumeRepository`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import decode_cursor, encode_cursor
from app.domain.value_objects.generated_document import CoverLetterContent
from app.infrastructure.db.models import GeneratedCoverLetter, Job


class SqlAlchemyGeneratedCoverLetterRepository:
    """SQLAlchemy-backed implementation of the `GeneratedCoverLetterRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, profile_id: UUID, job: Job, content: CoverLetterContent, file_path: str
    ) -> GeneratedCoverLetter:
        cover_letter = GeneratedCoverLetter(
            profile_id=profile_id,
            job_id=job.id,
            body=content.body,
            file_path=file_path,
        )
        self._session.add(cover_letter)
        await self._session.flush()
        await self._session.refresh(cover_letter, attribute_names=["job"])
        return cover_letter

    async def get_by_id(self, *, profile_id: UUID, cover_letter_id: UUID) -> GeneratedCoverLetter | None:
        stmt = select(GeneratedCoverLetter).where(
            GeneratedCoverLetter.id == cover_letter_id, GeneratedCoverLetter.profile_id == profile_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_profile(
        self, *, profile_id: UUID, cursor: str | None, limit: int
    ) -> tuple[list[GeneratedCoverLetter], str | None]:
        stmt = (
            select(GeneratedCoverLetter)
            .where(GeneratedCoverLetter.profile_id == profile_id)
            .order_by(GeneratedCoverLetter.created_at.desc(), GeneratedCoverLetter.id.desc())
            .limit(limit + 1)
        )

        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                (GeneratedCoverLetter.created_at < cursor_created_at)
                | (
                    (GeneratedCoverLetter.created_at == cursor_created_at)
                    & (GeneratedCoverLetter.id < cursor_id)
                )
            )

        result = await self._session.execute(stmt)
        cover_letters = list(result.scalars().all())

        next_cursor: str | None = None
        if len(cover_letters) > limit:
            cover_letters = cover_letters[:limit]
            last = cover_letters[-1]
            next_cursor = encode_cursor(created_at=last.created_at, id_=last.id)

        return cover_letters, next_cursor
