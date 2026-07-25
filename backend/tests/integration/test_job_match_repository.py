"""Integration tests for `SqlAlchemyJobMatchRepository` against real PostgreSQL.

Proves what fakes can't: the `profile_id`/`job_id` foreign keys are real,
`matched_skills`/`missing_skills` round-trip through JSONB correctly, and
pagination ordering works — matching the pattern established for jobs
(Milestone 3) and profiles (Milestone 4).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.profile import Profile
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.domain.value_objects.match_result import MatchResult
from app.infrastructure.db.repositories.job_match_repository import SqlAlchemyJobMatchRepository
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository


async def _seeded_profile(session: AsyncSession) -> Profile:
    repository = SqlAlchemyProfileRepository(session)
    profile = await repository.create(Profile(full_name="Ada Lovelace", email="ada@example.com"))
    await session.flush()
    return profile


async def _seeded_job(session: AsyncSession, *, external_id: str = "job-1"):
    repository = SqlAlchemyJobRepository(session)
    job = await repository.create(
        NormalizedJobPosting(source="adzuna", external_id=external_id, title="Cloud Engineer", company="Acme")
    )
    await session.flush()
    return job


@pytest.mark.asyncio
async def test_create_persists_a_match(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    job = await _seeded_job(db_session)
    repository = SqlAlchemyJobMatchRepository(db_session)

    result = MatchResult(
        score=Decimal("87.50"),
        rationale="Strong overlap.",
        matched_skills=["Python"],
        missing_skills=["Kubernetes"],
    )

    match = await repository.create(profile_id=profile.id, job=job, result=result)  # type: ignore[arg-type]
    await db_session.flush()

    assert match.profile_id == profile.id
    assert match.job_id == job.id
    assert match.match_score == Decimal("87.50")
    assert match.matched_skills == ["Python"]
    assert match.missing_skills == ["Kubernetes"]
    assert match.job.title == "Cloud Engineer"


@pytest.mark.asyncio
async def test_create_allows_rescoring_the_same_job(db_session: AsyncSession) -> None:
    """A match is a point-in-time snapshot — scoring the same profile/job
    pair twice must produce two rows, not update-in-place or conflict.
    """
    profile = await _seeded_profile(db_session)
    job = await _seeded_job(db_session)
    repository = SqlAlchemyJobMatchRepository(db_session)

    first = await repository.create(
        profile_id=profile.id,  # type: ignore[arg-type]
        job=job,
        result=MatchResult(score=Decimal("60"), rationale="First pass."),
    )
    second = await repository.create(
        profile_id=profile.id,  # type: ignore[arg-type]
        job=job,
        result=MatchResult(score=Decimal("75"), rationale="Re-scored after profile update."),
    )
    await db_session.flush()

    assert first.id != second.id
    matches, _ = await repository.list_for_profile(profile_id=profile.id, cursor=None, limit=10)  # type: ignore[arg-type]
    assert len(matches) == 2


@pytest.mark.asyncio
async def test_list_for_profile_orders_newest_first_and_paginates(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    repository = SqlAlchemyJobMatchRepository(db_session)

    for i in range(3):
        job = await _seeded_job(db_session, external_id=f"job-{i}")
        await repository.create(
            profile_id=profile.id,  # type: ignore[arg-type]
            job=job,
            result=MatchResult(score=Decimal(50 + i), rationale=f"Pass {i}"),
        )
        await db_session.flush()
        await asyncio.sleep(0.01)

    first_page, cursor = await repository.list_for_profile(profile_id=profile.id, cursor=None, limit=2)  # type: ignore[arg-type]
    assert [m.reasoning for m in first_page] == ["Pass 2", "Pass 1"]
    assert cursor is not None

    second_page, next_cursor = await repository.list_for_profile(
        profile_id=profile.id, cursor=cursor, limit=2  # type: ignore[arg-type]
    )
    assert [m.reasoning for m in second_page] == ["Pass 0"]
    assert next_cursor is None


@pytest.mark.asyncio
async def test_list_for_profile_returns_empty_when_no_matches_exist(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    repository = SqlAlchemyJobMatchRepository(db_session)

    matches, cursor = await repository.list_for_profile(profile_id=profile.id, cursor=None, limit=10)  # type: ignore[arg-type]

    assert matches == []
    assert cursor is None
