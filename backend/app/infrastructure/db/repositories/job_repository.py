"""Job repository.

Implements the `JobRepository` protocol from `app/application/jobs/ports.py`
against SQLAlchemy/PostgreSQL — the only place in the codebase that knows
`Job` is a SQLAlchemy model or that duplicate detection is a Postgres
unique-constraint violation under the hood.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.jobs.ingestion_service import JobAlreadyExistsError
from app.core.pagination import decode_cursor, encode_cursor
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.models import Job


class SqlAlchemyJobRepository:
    """SQLAlchemy-backed implementation of the `JobRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_source_and_external_id(self, *, source: str, external_id: str) -> Job | None:
        stmt = select(Job).where(Job.source == source, Job.external_id == external_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, posting: NormalizedJobPosting) -> Job:
        # `begin_nested()` opens a SAVEPOINT; explicit commit/rollback on
        # the returned transaction (rather than relying on `async with`'s
        # implicit cleanup) is the pattern SQLAlchemy's own docs recommend
        # for "flush might fail, only roll back to the savepoint" — found
        # to matter in practice: the `async with` form left the *outer*
        # session transaction deactivated after a caught IntegrityError,
        # breaking any further use of the session in the same request.
        nested = await self._session.begin_nested()
        job = Job(
            source=posting.source,
            external_id=posting.external_id,
            title=posting.title,
            company=posting.company,
            location=posting.location,
            description=posting.description,
            url=posting.url,
        )
        self._session.add(job)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await nested.rollback()
            msg = f"Job already exists for source={posting.source!r} external_id={posting.external_id!r}."
            raise JobAlreadyExistsError(msg) from exc
        else:
            await nested.commit()
        return job

    async def list_jobs(self, *, cursor: str | None, limit: int) -> tuple[list[Job], str | None]:
        stmt = select(Job).order_by(Job.created_at.desc(), Job.id.desc()).limit(limit + 1)

        if cursor is not None:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                (Job.created_at < cursor_created_at)
                | ((Job.created_at == cursor_created_at) & (Job.id < cursor_id))
            )

        result = await self._session.execute(stmt)
        jobs = list(result.scalars().all())

        next_cursor: str | None = None
        if len(jobs) > limit:
            jobs = jobs[:limit]
            last = jobs[-1]
            next_cursor = encode_cursor(created_at=last.created_at, id_=last.id)

        return jobs, next_cursor
