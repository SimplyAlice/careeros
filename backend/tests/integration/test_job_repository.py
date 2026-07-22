"""Integration tests for `SqlAlchemyJobRepository` against real PostgreSQL.

Complements `tests/unit/test_job_ingestion_service.py` (which uses fakes
and never touches a database): these tests exist specifically to prove
the repository's SAVEPOINT-based duplicate handling and cursor pagination
work against the real `uq_jobs_source_external_id` constraint and real
`created_at` ordering — behavior a fake repository can't validate.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.jobs.ingestion_service import JobAlreadyExistsError
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository


def _posting(external_id: str, title: str = "Cloud Engineer") -> NormalizedJobPosting:
    return NormalizedJobPosting(
        source="adzuna",
        external_id=external_id,
        title=title,
        company="Example Corp",
        location="Remote",
    )


@pytest.mark.asyncio
async def test_create_then_lookup_round_trips(db_session: AsyncSession) -> None:
    repository = SqlAlchemyJobRepository(db_session)

    created = await repository.create(_posting("rt-1"))
    await db_session.flush()

    found = await repository.get_by_source_and_external_id(source="adzuna", external_id="rt-1")

    assert found is not None
    assert found.id == created.id
    assert found.title == "Cloud Engineer"


@pytest.mark.asyncio
async def test_lookup_returns_none_when_not_found(db_session: AsyncSession) -> None:
    repository = SqlAlchemyJobRepository(db_session)

    found = await repository.get_by_source_and_external_id(source="adzuna", external_id="does-not-exist")

    assert found is None


@pytest.mark.asyncio
async def test_create_duplicate_raises_job_already_exists_error(db_session: AsyncSession) -> None:
    """Proves the SAVEPOINT-wrapped `create()` translates the real
    `uq_jobs_source_external_id` database constraint into
    `JobAlreadyExistsError` — and that the session remains usable
    afterward (the whole point of scoping the failure to a SAVEPOINT).
    """
    repository = SqlAlchemyJobRepository(db_session)

    await repository.create(_posting("dup-1"))
    await db_session.flush()

    with pytest.raises(JobAlreadyExistsError):
        await repository.create(_posting("dup-1", title="A different title"))

    # The session must still be usable after the caught duplicate — this
    # is exactly what the SAVEPOINT (not the whole transaction) rollback
    # buys us; a subsequent, unrelated operation should succeed normally.
    await repository.create(_posting("dup-2"))
    await db_session.flush()
    found = await repository.get_by_source_and_external_id(source="adzuna", external_id="dup-2")
    assert found is not None


@pytest.mark.asyncio
async def test_list_jobs_orders_newest_first_and_paginates(db_session: AsyncSession) -> None:
    repository = SqlAlchemyJobRepository(db_session)

    for i in range(5):
        await repository.create(_posting(f"page-{i}"))
        await db_session.flush()
        # created_at has second-level meaningful ordering in Postgres,
        # but sqlite-speed test inserts can land in the same instant —
        # a tiny sleep guarantees a strict, testable creation order here.
        await asyncio.sleep(0.01)

    first_page, cursor_1 = await repository.list_jobs(cursor=None, limit=2)
    assert [j.external_id for j in first_page] == ["page-4", "page-3"]
    assert cursor_1 is not None

    second_page, cursor_2 = await repository.list_jobs(cursor=cursor_1, limit=2)
    assert [j.external_id for j in second_page] == ["page-2", "page-1"]
    assert cursor_2 is not None

    third_page, cursor_3 = await repository.list_jobs(cursor=cursor_2, limit=2)
    assert [j.external_id for j in third_page] == ["page-0"]
    assert cursor_3 is None  # no more pages


@pytest.mark.asyncio
async def test_list_jobs_returns_empty_when_no_jobs_exist(db_session: AsyncSession) -> None:
    repository = SqlAlchemyJobRepository(db_session)

    jobs, cursor = await repository.list_jobs(cursor=None, limit=20)

    assert jobs == []
    assert cursor is None
