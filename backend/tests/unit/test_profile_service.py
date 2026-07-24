"""Unit tests for `ProfileService`, using an in-memory fake repository.

No database — this proves the use-case orchestration (create rejects a
second profile, update requires an existing one, partial patches apply
correctly) independent of persistence, matching the pattern established
for `JobIngestionService` in Milestone 3.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.application.profile.dtos import EducationInput, ExperienceInput, ProfileCreateData
from app.application.profile.errors import ProfileAlreadyExistsError, ProfileNotFoundError
from app.application.profile.profile_service import ProfileService
from app.domain.entities.profile import DuplicateSkillError, Profile


class FakeProfileRepository:
    def __init__(self) -> None:
        self._profile: Profile | None = None
        self._next_id = 1

    async def get(self) -> Profile | None:
        return self._profile

    async def create(self, profile: Profile) -> Profile:
        if self._profile is not None:
            msg = "already exists"
            raise ProfileAlreadyExistsError(msg)
        profile.id = uuid.UUID(int=self._next_id)
        self._profile = profile
        return profile

    async def update(self, profile: Profile) -> Profile:
        if self._profile is None:
            msg = "no profile"
            raise ProfileNotFoundError(msg)
        self._profile = profile
        return profile


def _create_data(**overrides: object) -> ProfileCreateData:
    defaults: dict[str, object] = {"full_name": "Ada Lovelace", "email": "ada@example.com"}
    defaults.update(overrides)
    return ProfileCreateData(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_profile_raises_when_none_exists() -> None:
    service = ProfileService(FakeProfileRepository())

    with pytest.raises(ProfileNotFoundError):
        await service.get_profile()


@pytest.mark.asyncio
async def test_create_then_get_round_trips() -> None:
    service = ProfileService(FakeProfileRepository())

    created = await service.create_profile(_create_data())
    fetched = await service.get_profile()

    assert fetched.email == created.email == "ada@example.com"


@pytest.mark.asyncio
async def test_create_twice_raises_already_exists() -> None:
    service = ProfileService(FakeProfileRepository())
    await service.create_profile(_create_data())

    with pytest.raises(ProfileAlreadyExistsError):
        await service.create_profile(_create_data(email="someone-else@example.com"))


@pytest.mark.asyncio
async def test_create_with_skills_and_experience_and_education() -> None:
    service = ProfileService(FakeProfileRepository())

    created = await service.create_profile(
        _create_data(
            skills=["Python", "Azure"],
            experience=[ExperienceInput(company="Acme", title="Engineer", start_date=date(2020, 1, 1))],
            education=[
                EducationInput(institution="MIT", qualification="BSc", start_year=2016, end_year=2020)
            ],
        )
    )

    assert [s.name for s in created.skills] == ["Python", "Azure"]
    assert created.experience[0].company == "Acme"
    assert created.education[0].institution == "MIT"


@pytest.mark.asyncio
async def test_update_profile_without_existing_profile_raises_not_found() -> None:
    service = ProfileService(FakeProfileRepository())

    with pytest.raises(ProfileNotFoundError):
        await service.update_profile({"headline": "New headline"})


@pytest.mark.asyncio
async def test_update_profile_applies_partial_changes() -> None:
    service = ProfileService(FakeProfileRepository())
    await service.create_profile(_create_data(headline="Old headline"))

    updated = await service.update_profile({"headline": "New headline"})

    assert updated.headline == "New headline"
    assert updated.full_name == "Ada Lovelace"  # untouched fields survive


@pytest.mark.asyncio
async def test_update_profile_replaces_skills_list() -> None:
    service = ProfileService(FakeProfileRepository())
    await service.create_profile(_create_data(skills=["Python"]))

    updated = await service.update_profile({"skills": ["Go", "Rust"]})

    assert [s.name for s in updated.skills] == ["Go", "Rust"]


@pytest.mark.asyncio
async def test_update_profile_rejects_duplicate_skills_in_patch() -> None:
    service = ProfileService(FakeProfileRepository())
    await service.create_profile(_create_data())

    with pytest.raises(DuplicateSkillError):
        await service.update_profile({"skills": ["Python", "python"]})


@pytest.mark.asyncio
async def test_update_profile_replaces_experience_list() -> None:
    service = ProfileService(FakeProfileRepository())
    await service.create_profile(_create_data())

    updated = await service.update_profile(
        {"experience": [ExperienceInput(company="NewCo", title="Lead Engineer", start_date=date(2021, 1, 1))]}
    )

    assert len(updated.experience) == 1
    assert updated.experience[0].company == "NewCo"
