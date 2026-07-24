"""Profile management use cases.

No FastAPI, no SQLAlchemy — only the domain entities and the
`ProfileRepository` port. This is what `api/v1/profile.py` calls; it's
also exactly what a future CLI, admin script, or (once auth exists) a
per-user variant of this service would call, unchanged.
"""

from __future__ import annotations

from typing import Any

from app.application.profile.dtos import ProfileCreateData
from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.core.logging import get_logger
from app.domain.entities.profile import Education, Experience, Profile, Skill

logger = get_logger(__name__)


class ProfileService:
    """Orchestrates the create/retrieve/update use cases for the single profile."""

    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    async def get_profile(self) -> Profile:
        """Return the profile, raising if it hasn't been created yet."""
        profile = await self._repository.get()
        if profile is None:
            msg = "No profile has been created yet."
            raise ProfileNotFoundError(msg)
        return profile

    async def create_profile(self, data: ProfileCreateData) -> Profile:
        """Create the (one and only) profile.

        Constructing the `Profile` domain entity runs every business-rule
        validation in `Profile.__post_init__` before persistence is even
        attempted — invalid data never reaches the repository.
        """
        profile = Profile(
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            location=data.location,
            headline=data.headline,
            summary=data.summary,
            years_experience=data.years_experience,
            preferred_job_title=data.preferred_job_title,
            preferred_location=data.preferred_location,
            salary_expectation=data.salary_expectation,
            remote_preference=data.remote_preference,
            skills=[Skill(name=name) for name in data.skills],
            experience=[
                Experience(
                    company=item.company,
                    title=item.title,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    currently_working=item.currently_working,
                    description=item.description,
                )
                for item in data.experience
            ],
            education=[
                Education(
                    institution=item.institution,
                    qualification=item.qualification,
                    start_year=item.start_year,
                    field_of_study=item.field_of_study,
                    end_year=item.end_year,
                )
                for item in data.education
            ],
        )
        created = await self._repository.create(profile)
        logger.info("profile_created", profile_id=str(created.id))
        return created

    async def update_profile(self, changes: dict[str, Any]) -> Profile:
        """Apply a partial update to the existing profile.

        `changes` should already be filtered to only the fields the
        client actually provided (see `Profile.apply_patch`'s docstring
        for why). `skills`, `experience`, and `education` — if present —
        are handled as wholesale-replace operations, not merged item by
        item; merging a list of child entities field-by-field is a much
        more complex operation with its own ambiguities (what does it mean
        to "merge" two experience entries?) that isn't needed yet.
        """
        profile = await self.get_profile()

        core_changes = {
            key: value for key, value in changes.items() if key not in {"skills", "experience", "education"}
        }
        if core_changes:
            profile.apply_patch(core_changes)

        if "skills" in changes:
            skill_names: list[str] = changes["skills"] or []
            profile.replace_skills([Skill(name=name) for name in skill_names])

        if "experience" in changes:
            experience_items: list[Any] = changes["experience"] or []
            profile.replace_experience(
                [
                    Experience(
                        company=item.company,
                        title=item.title,
                        start_date=item.start_date,
                        end_date=item.end_date,
                        currently_working=item.currently_working,
                        description=item.description,
                    )
                    for item in experience_items
                ]
            )

        if "education" in changes:
            education_items: list[Any] = changes["education"] or []
            profile.replace_education(
                [
                    Education(
                        institution=item.institution,
                        qualification=item.qualification,
                        start_year=item.start_year,
                        field_of_study=item.field_of_study,
                        end_year=item.end_year,
                    )
                    for item in education_items
                ]
            )

        updated = await self._repository.update(profile)
        logger.info("profile_updated", profile_id=str(updated.id), changed_fields=sorted(changes.keys()))
        return updated
