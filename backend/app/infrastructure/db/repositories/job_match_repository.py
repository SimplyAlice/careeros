"""JobMatch repository.

Implements the `JobMatchRepository` protocol from
`app/application/scoring/ports.py` against SQLAlchemy — the only place in
the codebase that knows a `MatchResult` becomes a `job_matches` row, or
that listing is a `created_at DESC, id DESC` query.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import decode_cursor, encode_cursor
from app.domain.value_objects.match_result import MatchResult
from app.infrastructure.db.models import Job, JobMatch


class SqlAlchemyJobMatchRepository:
    """SQLAlchemy-backed implementation of the `JobMatchRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, profile_id: UUID, job: Job, result: MatchResult) -> JobMatch:
        match = JobMatch(
            profile_id=profile_id,
            job_id=job.id,
            match_score=result.score,
            reasoning=result.rationale,
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
        )
        self._session.add(match)
        await self._session.flush()
        await self._session.refresh(match, attribute_names=["job"])
        return match

    async def list_for_profile(
        self, *, profile_id: UUID, cursor: str | None, limit: int
    ) -> tuple[list[JobMatch], str | None]:
        stmt = (
            select(JobMatch)
            .where(JobMatch.profile_id == profile_id)
            .order_by(JobMatch.created_at.desc(), JobMatch.id.desc())
            .limit(limit + 1)
        )

        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                (JobMatch.created_at < cursor_created_at)
                | ((JobMatch.created_at == cursor_created_at) & (JobMatch.id < cursor_id))
            )

        result = await self._session.execute(stmt)
        matches = list(result.scalars().all())

        next_cursor: str | None = None
        if len(matches) > limit:
            matches = matches[:limit]
            last = matches[-1]
            next_cursor = encode_cursor(created_at=last.created_at, id_=last.id)

        return matches, next_cursor
