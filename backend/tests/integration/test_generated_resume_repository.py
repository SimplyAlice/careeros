"""Integration tests for `SqlAlchemyGeneratedResumeRepository` against real PostgreSQL."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.profile import Profile
from app.domain.value_objects.generated_document import TailoredResumeContent
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.repositories.generated_resume_repository import SqlAlchemyGeneratedResumeRepository
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
async def test_create_persists_a_general_resume(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    repository = SqlAlchemyGeneratedResumeRepository(db_session)
    content = TailoredResumeContent(professional_summary="Strong engineer.", emphasized_skills=["Python"])

    resume = await repository.create(
        profile_id=profile.id, job_id=None, content=content, file_path="/tmp/resume.pdf"  # type: ignore[arg-type]
    )
    await db_session.flush()

    assert resume.profile_id == profile.id
    assert resume.job_id is None
    assert resume.professional_summary == "Strong engineer."
    assert resume.emphasized_skills == ["Python"]
    assert resume.file_path == "/tmp/resume.pdf"


@pytest.mark.asyncio
async def test_create_persists_a_job_tailored_resume(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    job = await _seeded_job(db_session)
    repository = SqlAlchemyGeneratedResumeRepository(db_session)
    content = TailoredResumeContent(professional_summary="Tailored summary.")

    resume = await repository.create(
        profile_id=profile.id, job_id=job.id, content=content, file_path="/tmp/resume.pdf"  # type: ignore[arg-type]
    )
    await db_session.flush()

    assert resume.job_id == job.id
    assert resume.job.title == "Cloud Engineer"


@pytest.mark.asyncio
async def test_get_by_id_is_scoped_to_the_owning_profile(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    repository = SqlAlchemyGeneratedResumeRepository(db_session)
    content = TailoredResumeContent(professional_summary="Summary.")

    resume = await repository.create(
        profile_id=profile.id, job_id=None, content=content, file_path="/tmp/r.pdf"  # type: ignore[arg-type]
    )
    await db_session.flush()

    found = await repository.get_by_id(profile_id=profile.id, resume_id=resume.id)  # type: ignore[arg-type]
    assert found is not None

    not_found = await repository.get_by_id(profile_id=uuid.uuid4(), resume_id=resume.id)  # type: ignore[arg-type]
    assert not_found is None


@pytest.mark.asyncio
async def test_list_for_profile_orders_newest_first_and_paginates(db_session: AsyncSession) -> None:
    profile = await _seeded_profile(db_session)
    repository = SqlAlchemyGeneratedResumeRepository(db_session)

    for i in range(3):
        await repository.create(
            profile_id=profile.id,  # type: ignore[arg-type]
            job_id=None,
            content=TailoredResumeContent(professional_summary=f"Summary {i}"),
            file_path=f"/tmp/r{i}.pdf",
        )
        await db_session.flush()
        await asyncio.sleep(0.01)

    first_page, cursor = await repository.list_for_profile(profile_id=profile.id, cursor=None, limit=2)  # type: ignore[arg-type]
    assert [r.professional_summary for r in first_page] == ["Summary 2", "Summary 1"]
    assert cursor is not None

    second_page, next_cursor = await repository.list_for_profile(
        profile_id=profile.id, cursor=cursor, limit=2  # type: ignore[arg-type]
    )
    assert [r.professional_summary for r in second_page] == ["Summary 0"]
    assert next_cursor is None
