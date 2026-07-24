"""Integration tests for `SqlAlchemyProfileRepository` against real PostgreSQL.

Proves what a fake repository can't: the singleton database constraint,
the skills unique constraint, and cascade deletes actually work against
real Postgres — matching the pattern established for jobs in Milestone 3
(`tests/integration/test_job_repository.py`).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.profile.errors import ProfileAlreadyExistsError, ProfileNotFoundError
from app.domain.entities.profile import Education, Experience, Profile, RemotePreference, Skill
from app.infrastructure.db.models import Education as EducationOrm
from app.infrastructure.db.models import Experience as ExperienceOrm
from app.infrastructure.db.models import Profile as ProfileOrm
from app.infrastructure.db.models import Skill as SkillOrm
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository


def _profile(**overrides: object) -> Profile:
    defaults: dict[str, object] = {"full_name": "Ada Lovelace", "email": "ada@example.com"}
    defaults.update(overrides)
    return Profile(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_returns_none_when_no_profile_exists(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)

    result = await repository.get()

    assert result is None


@pytest.mark.asyncio
async def test_create_then_get_round_trips(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)

    created = await repository.create(
        _profile(
            headline="Cloud Engineer",
            years_experience=5,
            salary_expectation=Decimal("650000.00"),
            remote_preference=RemotePreference.REMOTE,
            skills=[Skill(name="Python"), Skill(name="Azure")],
        )
    )
    await db_session.flush()

    fetched = await repository.get()

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.headline == "Cloud Engineer"
    assert fetched.years_experience == 5
    assert fetched.salary_expectation == Decimal("650000.00")
    assert fetched.remote_preference is RemotePreference.REMOTE
    assert {s.name for s in fetched.skills} == {"Python", "Azure"}


@pytest.mark.asyncio
async def test_create_persists_experience_and_education(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)

    await repository.create(
        _profile(
            experience=[
                Experience(
                    company="Acme", title="Engineer", start_date=date(2020, 1, 1), currently_working=True
                )
            ],
            education=[Education(institution="MIT", qualification="BSc", start_year=2016, end_year=2020)],
        )
    )
    await db_session.flush()

    fetched = await repository.get()

    assert fetched is not None
    assert fetched.experience[0].company == "Acme"
    assert fetched.experience[0].currently_working is True
    assert fetched.education[0].institution == "MIT"


@pytest.mark.asyncio
async def test_create_second_profile_raises_already_exists(db_session: AsyncSession) -> None:
    """Proves the database-level singleton index (`ix_profiles_singleton`)
    actually rejects a second row — not just the application-level
    pre-check, which this test bypasses by calling `create()` directly
    twice without checking `get()` in between first.
    """
    repository = SqlAlchemyProfileRepository(db_session)
    await repository.create(_profile())
    await db_session.flush()

    with pytest.raises(ProfileAlreadyExistsError):
        await repository.create(_profile(email="someone-else@example.com"))

    # The session must remain usable after the caught error.
    fetched = await repository.get()
    assert fetched is not None
    assert fetched.email == "ada@example.com"


@pytest.mark.asyncio
async def test_update_persists_changes(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)
    created = await repository.create(_profile(headline="Old headline"))
    await db_session.flush()

    created.headline = "New headline"
    updated = await repository.update(created)
    await db_session.flush()

    assert updated.headline == "New headline"
    fetched = await repository.get()
    assert fetched is not None
    assert fetched.headline == "New headline"


@pytest.mark.asyncio
async def test_update_replaces_skills_wholesale(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)
    created = await repository.create(_profile(skills=[Skill(name="Python")]))
    await db_session.flush()

    created.replace_skills([Skill(name="Go"), Skill(name="Rust")])
    await repository.update(created)
    await db_session.flush()

    fetched = await repository.get()
    assert fetched is not None
    assert {s.name for s in fetched.skills} == {"Go", "Rust"}


@pytest.mark.asyncio
async def test_update_without_persisted_id_raises_not_found(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)
    never_persisted = _profile()

    with pytest.raises(ProfileNotFoundError):
        await repository.update(never_persisted)


@pytest.mark.asyncio
async def test_duplicate_skill_name_for_same_profile_is_rejected_at_db_level(
    db_session: AsyncSession,
) -> None:
    """The domain layer already rejects duplicate skills within one
    `Profile` object (see `tests/unit/test_profile_domain.py`) — this test
    proves the database's own `uq_skills_profile_id_name` constraint is
    the real backstop, by inserting around the domain check entirely.
    """
    repository = SqlAlchemyProfileRepository(db_session)
    created = await repository.create(_profile())
    await db_session.flush()

    db_session.add(SkillOrm(profile_id=created.id, name="Python"))
    db_session.add(SkillOrm(profile_id=created.id, name="Python"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_deleting_profile_cascades_to_children(db_session: AsyncSession) -> None:
    repository = SqlAlchemyProfileRepository(db_session)
    created = await repository.create(
        _profile(
            skills=[Skill(name="Python")],
            experience=[Experience(company="Acme", title="Engineer", start_date=date(2020, 1, 1))],
            education=[Education(institution="MIT", qualification="BSc", start_year=2016)],
        )
    )
    await db_session.flush()

    row = await db_session.get(ProfileOrm, created.id)
    assert row is not None
    await db_session.delete(row)
    await db_session.flush()

    remaining_skills = await db_session.execute(select(SkillOrm).where(SkillOrm.profile_id == created.id))
    remaining_experience = await db_session.execute(
        select(ExperienceOrm).where(ExperienceOrm.profile_id == created.id)
    )
    remaining_education = await db_session.execute(
        select(EducationOrm).where(EducationOrm.profile_id == created.id)
    )

    assert remaining_skills.first() is None
    assert remaining_experience.first() is None
    assert remaining_education.first() is None
