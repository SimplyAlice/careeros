"""Verifies that model relationships, cascades, and constraints behave as
designed — not just that the tables exist, but that the schema enforces
the rules `docs/architecture/database-design.md` documents.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Job,
    JobMatch,
    Resume,
    User,
)


async def _make_user(session: AsyncSession, *, email: str | None = None) -> User:
    # `password_hash` is a placeholder here — this test module exercises
    # relationships *involving* User (CandidateProfile, Resume, JobMatch,
    # Application), not authentication itself (see
    # `tests/unit/test_auth_service.py`/`tests/integration/test_auth_api.py`
    # for real password hashing). Required since Milestone 7 added the
    # column as NOT NULL.
    user = User(email=email or f"{uuid.uuid4()}@example.com", password_hash="not-a-real-hash")
    session.add(user)
    await session.flush()
    return user


async def _make_job(session: AsyncSession, *, external_id: str | None = None) -> Job:
    job = Job(
        source="adzuna",
        external_id=external_id or str(uuid.uuid4()),
        title="Cloud Engineer",
        company="Example Corp",
        location="Remote",
    )
    session.add(job)
    await session.flush()
    return job


@pytest.mark.asyncio
async def test_user_candidate_profile_one_to_one(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    profile = CandidateProfile(
        user_id=user.id,
        full_name="Ada Lovelace",
        skills=["Python", "Azure"],
    )
    db_session.add(profile)
    await db_session.flush()

    # Relationship navigates in both directions without an extra query
    # (lazy="selectin" — see app/infrastructure/db/models/user.py).
    await db_session.refresh(user, attribute_names=["candidate_profile"])
    assert user.candidate_profile is not None
    assert user.candidate_profile.full_name == "Ada Lovelace"
    assert profile.user.email == user.email


@pytest.mark.asyncio
async def test_candidate_profile_enforces_one_per_user(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add(CandidateProfile(user_id=user.id, full_name="First"))
    await db_session.flush()

    db_session.add(CandidateProfile(user_id=user.id, full_name="Second"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_has_many_resumes(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    db_session.add_all(
        [
            Resume(user_id=user.id, title="Cloud Resume", content="..."),
            Resume(user_id=user.id, title="Backend Resume", content="..."),
        ]
    )
    await db_session.flush()

    await db_session.refresh(user, attribute_names=["resumes"])
    assert {r.title for r in user.resumes} == {"Cloud Resume", "Backend Resume"}


@pytest.mark.asyncio
async def test_job_match_links_user_and_job(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    job = await _make_job(db_session)

    match = JobMatch(user_id=user.id, job_id=job.id, match_score=87.5, reasoning="Strong skills overlap.")
    db_session.add(match)
    await db_session.flush()

    await db_session.refresh(user, attribute_names=["job_matches"])
    await db_session.refresh(job, attribute_names=["job_matches"])
    assert user.job_matches[0].job_id == job.id
    assert job.job_matches[0].user_id == user.id


@pytest.mark.asyncio
async def test_job_match_score_out_of_range_is_rejected(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    job = await _make_job(db_session)

    db_session.add(JobMatch(user_id=user.id, job_id=job.id, match_score=150))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_application_default_status_is_saved(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    job = await _make_job(db_session)

    application = Application(user_id=user.id, job_id=job.id)
    db_session.add(application)
    await db_session.flush()
    await db_session.refresh(application)

    assert application.status == ApplicationStatus.SAVED


@pytest.mark.asyncio
async def test_application_duplicate_for_same_user_and_job_is_rejected(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    job = await _make_job(db_session)

    db_session.add(Application(user_id=user.id, job_id=job.id, status=ApplicationStatus.SAVED))
    await db_session.flush()

    db_session.add(Application(user_id=user.id, job_id=job.id, status=ApplicationStatus.REVIEWING))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_job_source_and_external_id_uniqueness(db_session: AsyncSession) -> None:
    await _make_job(db_session, external_id="dup-123")

    db_session.add(Job(source="adzuna", external_id="dup-123", title="Other Role", company="Other Co"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_deleting_user_cascades_to_dependent_rows(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    job = await _make_job(db_session)
    db_session.add(CandidateProfile(user_id=user.id, full_name="Cascade Test"))
    db_session.add(Resume(user_id=user.id, title="Resume"))
    db_session.add(Application(user_id=user.id, job_id=job.id))
    await db_session.flush()

    await db_session.delete(user)
    await db_session.flush()

    remaining_profiles = await db_session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    remaining_applications = await db_session.execute(
        select(Application).where(Application.user_id == user.id)
    )

    assert remaining_profiles.first() is None
    assert remaining_applications.first() is None
