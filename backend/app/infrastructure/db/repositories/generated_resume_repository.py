"""GeneratedResume repository.

Implements `GeneratedResumeRepository` (`app/application/documents/ports.py`)
against SQLAlchemy, following the same shape as `SqlAlchemyJobMatchRepository`
(Milestone 5): create persists a new versioned row, listing is cursor
paginated newest-first.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import decode_cursor, encode_cursor
from app.domain.value_objects.generated_document import TailoredResumeContent
from app.infrastructure.db.models import GeneratedResume


class SqlAlchemyGeneratedResumeRepository:
    """SQLAlchemy-backed implementation of the `GeneratedResumeRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, profile_id: UUID, job_id: UUID | None, content: TailoredResumeContent, file_path: str
    ) -> GeneratedResume:
        resume = GeneratedResume(
            profile_id=profile_id,
            job_id=job_id,
            professional_summary=content.professional_summary,
            emphasized_skills=content.emphasized_skills,
            file_path=file_path,
        )
        self._session.add(resume)
        await self._session.flush()
        await self._session.refresh(resume, attribute_names=["job"])
        return resume

    async def get_by_id(self, *, profile_id: UUID, resume_id: UUID) -> GeneratedResume | None:
        stmt = select(GeneratedResume).where(
            GeneratedResume.id == resume_id, GeneratedResume.profile_id == profile_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_profile(
        self, *, profile_id: UUID, cursor: str | None, limit: int
    ) -> tuple[list[GeneratedResume], str | None]:
        stmt = (
            select(GeneratedResume)
            .where(GeneratedResume.profile_id == profile_id)
            .order_by(GeneratedResume.created_at.desc(), GeneratedResume.id.desc())
            .limit(limit + 1)
        )

        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                (GeneratedResume.created_at < cursor_created_at)
                | ((GeneratedResume.created_at == cursor_created_at) & (GeneratedResume.id < cursor_id))
            )

        result = await self._session.execute(stmt)
        resumes = list(result.scalars().all())

        next_cursor: str | None = None
        if len(resumes) > limit:
            resumes = resumes[:limit]
            last = resumes[-1]
            next_cursor = encode_cursor(created_at=last.created_at, id_=last.id)

        return resumes, next_cursor
