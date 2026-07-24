"""Profile repository.

Implements `ProfileRepository` (application layer) against SQLAlchemy —
the only place in the codebase that knows `Profile` is a table with child
tables, or that "no profile exists yet" is `SELECT ... LIMIT 1` returning
nothing.

This is also the translation boundary between the domain entity
(`app.domain.entities.profile.Profile`, imported here as `ProfileEntity`)
and the ORM model (`app.infrastructure.db.models.Profile`, imported as
`ProfileOrm`) — the two are unrelated classes that happen to share a name,
by design (see `app/domain/entities/profile.py`'s module docstring).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.profile.errors import ProfileAlreadyExistsError, ProfileNotFoundError
from app.domain.entities.profile import Education as EducationEntity
from app.domain.entities.profile import Experience as ExperienceEntity
from app.domain.entities.profile import Profile as ProfileEntity
from app.domain.entities.profile import ResumeMetadata as ResumeMetadataEntity
from app.domain.entities.profile import Skill as SkillEntity
from app.infrastructure.db.models import Education as EducationOrm
from app.infrastructure.db.models import Experience as ExperienceOrm
from app.infrastructure.db.models import Profile as ProfileOrm
from app.infrastructure.db.models import Skill as SkillOrm


class SqlAlchemyProfileRepository:
    """SQLAlchemy-backed implementation of the `ProfileRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> ProfileEntity | None:
        stmt = select(ProfileOrm).options(
            selectinload(ProfileOrm.skills),
            selectinload(ProfileOrm.experience_entries),
            selectinload(ProfileOrm.education_entries),
            selectinload(ProfileOrm.resumes),
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return _to_entity(row) if row is not None else None

    async def create(self, profile: ProfileEntity) -> ProfileEntity:
        row = ProfileOrm(
            full_name=profile.full_name,
            email=profile.email,
            phone=profile.phone,
            location=profile.location,
            headline=profile.headline,
            summary=profile.summary,
            years_experience=profile.years_experience,
            preferred_job_title=profile.preferred_job_title,
            preferred_location=profile.preferred_location,
            salary_expectation=profile.salary_expectation,
            remote_preference=profile.remote_preference,
            skills=[SkillOrm(name=skill.name) for skill in profile.skills],
            experience_entries=[_experience_entity_to_orm(item) for item in profile.experience],
            education_entries=[_education_entity_to_orm(item) for item in profile.education],
        )
        # SAVEPOINT-scoped, not a full session rollback: a plain
        # `session.rollback()` on IntegrityError would undo the *entire*
        # transaction, including any prior work already flushed in this
        # same session — the exact bug found (and fixed the same way) in
        # `SqlAlchemyJobRepository.create()` during Milestone 3. Explicit
        # commit/rollback on the nested transaction (not `async with`) is
        # the pattern that reliably restores session state afterward.
        nested = await self._session.begin_nested()
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await nested.rollback()
            msg = "A profile already exists — only one local profile is supported."
            raise ProfileAlreadyExistsError(msg) from exc
        else:
            await nested.commit()
        await self._session.refresh(
            row,
            attribute_names=["skills", "experience_entries", "education_entries", "resumes", "updated_at"],
        )
        return _to_entity(row)

    async def update(self, profile: ProfileEntity) -> ProfileEntity:
        if profile.id is None:
            msg = "Cannot update a profile that has never been persisted."
            raise ProfileNotFoundError(msg)

        row = await self._session.get(ProfileOrm, profile.id)
        if row is None:
            msg = "No profile has been created yet."
            raise ProfileNotFoundError(msg)

        row.full_name = profile.full_name
        row.email = profile.email
        row.phone = profile.phone
        row.location = profile.location
        row.headline = profile.headline
        row.summary = profile.summary
        row.years_experience = profile.years_experience
        row.preferred_job_title = profile.preferred_job_title
        row.preferred_location = profile.preferred_location
        row.salary_expectation = profile.salary_expectation
        row.remote_preference = profile.remote_preference

        # Wholesale replace for child collections — `cascade="all,
        # delete-orphan"` (set on the `Profile` ORM relationships) means
        # reassigning the list deletes rows no longer present and inserts
        # the new ones in a single flush, matching the domain layer's
        # `replace_skills`/`replace_experience`/`replace_education`
        # semantics exactly.
        row.skills = [SkillOrm(name=skill.name) for skill in profile.skills]
        row.experience_entries = [_experience_entity_to_orm(item) for item in profile.experience]
        row.education_entries = [_education_entity_to_orm(item) for item in profile.education]

        await self._session.flush()
        await self._session.refresh(
            row,
            attribute_names=["skills", "experience_entries", "education_entries", "resumes", "updated_at"],
        )
        return _to_entity(row)


def _experience_entity_to_orm(item: ExperienceEntity) -> ExperienceOrm:
    return ExperienceOrm(
        company=item.company,
        title=item.title,
        start_date=item.start_date,
        end_date=item.end_date,
        currently_working=item.currently_working,
        description=item.description,
    )


def _education_entity_to_orm(item: EducationEntity) -> EducationOrm:
    return EducationOrm(
        institution=item.institution,
        qualification=item.qualification,
        start_year=item.start_year,
        field_of_study=item.field_of_study,
        end_year=item.end_year,
    )


def _to_entity(row: ProfileOrm) -> ProfileEntity:
    """Translate a fully-loaded `ProfileOrm` row into the domain entity.

    Constructing `ProfileEntity` here re-runs `Profile.__post_init__`
    validation against data already known-valid (it was validated before
    being persisted) — a harmless, cheap re-check, not redundant work
    worth avoiding: it also guards against data that entered the database
    some other way (a manual fix, a future admin tool) being silently
    treated as valid.
    """
    return ProfileEntity(
        id=row.id,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        location=row.location,
        headline=row.headline,
        summary=row.summary,
        years_experience=row.years_experience,
        preferred_job_title=row.preferred_job_title,
        preferred_location=row.preferred_location,
        salary_expectation=row.salary_expectation,
        remote_preference=row.remote_preference,
        skills=[SkillEntity(id=s.id, name=s.name) for s in row.skills],
        experience=[
            ExperienceEntity(
                id=e.id,
                company=e.company,
                title=e.title,
                start_date=e.start_date,
                end_date=e.end_date,
                currently_working=e.currently_working,
                description=e.description,
            )
            for e in row.experience_entries
        ],
        education=[
            EducationEntity(
                id=ed.id,
                institution=ed.institution,
                qualification=ed.qualification,
                start_year=ed.start_year,
                field_of_study=ed.field_of_study,
                end_year=ed.end_year,
            )
            for ed in row.education_entries
        ],
        resumes=[
            ResumeMetadataEntity(id=r.id, filename=r.filename, uploaded_at=r.uploaded_at) for r in row.resumes
        ],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
