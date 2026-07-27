"""Integration tests for `SqlAlchemyGeneratedCoverLetterRepository` against real PostgreSQL."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.profile import Profile
from app.domain.value_objects.generated_document import CoverLetterContent
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.repositories.generated_cover_letter_repository import (
    SqlAlchemyGeneratedCoverLetterRepository,
)
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository


async def _seeded_profile(session: AsyncSession) -> Profile:
    profile = await SqlAlchemyProfileRepository(session).create(
        Profile(full_name="Ada Lovelace", email="ada@example.com")
    )
    await session.flush()
    return profile


async def _seeded_job(session: AsyncSession, *, external_id: str = "job-1"):
    job = await SqlAlchemyJobRepository(session).create(
        NormalizedJobPosting(source="adzuna", external_id=external_id, title="Cloud Engineer", company="Acme")
    )
    await session.flush()
    return job


@pytest.mark.asyncio
async def test_create_persists_a_cover_letter(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    job = await _seeded_job(db_session)
    repository = SqlAlchemyGeneratedCoverLetterRepository(db_session)
    content = CoverLetterContent(body="I would love to bring my skills to this role.")

    cover_letter = await repository.create(
        profile_id=profile.id, job=job, content=content, file_path="/tmp/cover.pdf"  # type: ignore[arg-type]
    )
    await db_session.flush()

    assert cover_letter.profile_id == profile.id
    assert cover_letter.job_id == job.id
    assert cover_letter.body == "I would love to bring my skills to this role."
    assert cover_letter.job.title == "Cloud Engineer"


@pytest.mark.asyncio
async def test_get_by_id_is_scoped_to_the_owning_profile(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    job = await _seeded_job(db_session)
    repository = SqlAlchemyGeneratedCoverLetterRepository(db_session)
    content = CoverLetterContent(body="Body text.")

    cover_letter = await repository.create(
        profile_id=profile.id, job=job, content=content, file_path="/tmp/c.pdf"  # type: ignore[arg-type]
    )
    await db_session.flush()

    found = await repository.get_by_id(profile_id=profile.id, cover_letter_id=cover_letter.id)  # type: ignore[arg-type]
    assert found is not None

    not_found = await repository.get_by_id(
        profile_id=uuid.uuid4(), cover_letter_id=cover_letter.id  # type: ignore[arg-type]
    )
    assert not_found is None


@pytest.mark.asyncio
async def test_list_for_profile_orders_newest_first_and_paginates(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    repository = SqlAlchemyGeneratedCoverLetterRepository(db_session)

    for i in range(3):
        job = await _seeded_job(db_session, external_id=f"job-{i}")
        await repository.create(
            profile_id=profile.id,  # type: ignore[arg-type]
            job=job,
            content=CoverLetterContent(body=f"Body {i}"),
            file_path=f"/tmp/c{i}.pdf",
        )
        await db_session.flush()
        await asyncio.sleep(0.01)

    first_page, cursor = await repository.list_for_profile(profile_id=profile.id, cursor=None, limit=2)  # type: ignore[arg-type]
    assert [cl.body for cl in first_page] == ["Body 2", "Body 1"]
    assert cursor is not None

    second_page, next_cursor = await repository.list_for_profile(
        profile_id=profile.id, cursor=cursor, limit=2  # type: ignore[arg-type]
    )
    assert [cl.body for cl in second_page] == ["Body 0"]
    assert next_cursor is None
