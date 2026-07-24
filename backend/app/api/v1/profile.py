"""Profile API — manage the single local profile.

Unauthenticated, per Milestone 4's explicit scope (see
`docs/adr/0012-profile-management.md`): there is exactly one profile in
the system and no user to authenticate as yet.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_profile_service
from app.application.profile.dtos import EducationInput, ExperienceInput, ProfileCreateData
from app.application.profile.errors import ProfileAlreadyExistsError, ProfileNotFoundError
from app.application.profile.profile_service import ProfileService
from app.domain.entities.profile import ProfileValidationError, RemotePreference

router = APIRouter(prefix="/profile", tags=["profile"])


# --- Read schemas ------------------------------------------------------------


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company: str
    title: str
    start_date: date
    end_date: date | None
    currently_working: bool
    description: str | None


class EducationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    institution: str
    qualification: str
    field_of_study: str | None
    start_year: int
    end_year: int | None


class ResumeMetadataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    uploaded_at: datetime


class ProfileRead(BaseModel):
    """The full profile, including its child collections."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: str | None
    location: str | None
    headline: str | None
    summary: str | None
    years_experience: int
    preferred_job_title: str | None
    preferred_location: str | None
    salary_expectation: Decimal | None
    remote_preference: RemotePreference
    skills: list[SkillRead]
    experience: list[ExperienceRead]
    education: list[EducationRead]
    resumes: list[ResumeMetadataRead]
    created_at: datetime | None
    updated_at: datetime | None


# --- Write schemas -----------------------------------------------------------


class ExperienceWrite(BaseModel):
    company: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    start_date: date
    end_date: date | None = None
    currently_working: bool = False
    description: str | None = Field(default=None, max_length=5000)

    def to_input(self) -> ExperienceInput:
        return ExperienceInput(
            company=self.company,
            title=self.title,
            start_date=self.start_date,
            end_date=self.end_date,
            currently_working=self.currently_working,
            description=self.description,
        )


class EducationWrite(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255)
    qualification: str = Field(..., min_length=1, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_year: int
    end_year: int | None = None

    def to_input(self) -> EducationInput:
        return EducationInput(
            institution=self.institution,
            qualification=self.qualification,
            start_year=self.start_year,
            field_of_study=self.field_of_study,
            end_year=self.end_year,
        )


class ProfileCreateRequest(BaseModel):
    """Body for `POST /api/v1/profile`. Field-level constraints (min/max
    length, `ge`) use FastAPI/Pydantic's own validation, producing the
    standard 422 response — deeper business rules (email format, no
    duplicate skills, salary sanity) run in the domain layer and are
    translated to a matching error response by this router.
    """

    full_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=5000)
    years_experience: int = Field(default=0, ge=0, le=70)
    preferred_job_title: str | None = Field(default=None, max_length=255)
    preferred_location: str | None = Field(default=None, max_length=255)
    salary_expectation: Decimal | None = Field(default=None, ge=0)
    remote_preference: RemotePreference = RemotePreference.FLEXIBLE
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceWrite] = Field(default_factory=list)
    education: list[EducationWrite] = Field(default_factory=list)

    @field_validator("skills")
    @classmethod
    def _skills_non_empty(cls, value: list[str]) -> list[str]:
        return [name for name in (v.strip() for v in value) if name]

    def to_create_data(self) -> ProfileCreateData:
        return ProfileCreateData(
            full_name=self.full_name,
            email=self.email,
            phone=self.phone,
            location=self.location,
            headline=self.headline,
            summary=self.summary,
            years_experience=self.years_experience,
            preferred_job_title=self.preferred_job_title,
            preferred_location=self.preferred_location,
            salary_expectation=self.salary_expectation,
            remote_preference=self.remote_preference,
            skills=self.skills,
            experience=[item.to_input() for item in self.experience],
            education=[item.to_input() for item in self.education],
        )


class ProfilePatchRequest(BaseModel):
    """Body for `PATCH /api/v1/profile`.

    Every field is optional and defaults to `None` — but "omitted" and
    "explicitly null" are still distinguished correctly, because the
    router reads this via `model_dump(exclude_unset=True)` rather than
    treating every `None` the same way. `skills`/`experience`/`education`,
    when included, wholesale-replace the existing list (see
    `ProfileService.update_profile`'s docstring for why merging item-by-item
    isn't supported).
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=5000)
    years_experience: int | None = Field(default=None, ge=0, le=70)
    preferred_job_title: str | None = Field(default=None, max_length=255)
    preferred_location: str | None = Field(default=None, max_length=255)
    salary_expectation: Decimal | None = Field(default=None, ge=0)
    remote_preference: RemotePreference | None = None
    skills: list[str] | None = None
    experience: list[ExperienceWrite] | None = None
    education: list[EducationWrite] | None = None

    def to_changes(self) -> dict[str, Any]:
        """Only the fields actually present in the request, with nested
        write-schemas converted to application-layer DTOs.
        """
        raw = self.model_dump(exclude_unset=True)
        if "experience" in raw and raw["experience"] is not None:
            raw["experience"] = [item.to_input() for item in (self.experience or [])]
        if "education" in raw and raw["education"] is not None:
            raw["education"] = [item.to_input() for item in (self.education or [])]
        return raw


# --- Routes ------------------------------------------------------------------


@router.get("", response_model=ProfileRead, summary="Get the profile")
async def get_profile(service: Annotated[ProfileService, Depends(get_profile_service)]) -> ProfileRead:
    """Return the profile, or 404 if it hasn't been created yet."""
    try:
        profile = await service.get_profile()
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProfileRead.model_validate(profile)


@router.post(
    "",
    response_model=ProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create the profile",
)
async def create_profile(
    body: ProfileCreateRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileRead:
    """Create the (one and only) profile. 409 if one already exists."""
    try:
        profile = await service.create_profile(body.to_create_data())
    except ProfileAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProfileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ProfileRead.model_validate(profile)


@router.patch("", response_model=ProfileRead, summary="Update the profile")
async def update_profile(
    body: ProfilePatchRequest,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileRead:
    """Partially update the profile. 404 if none exists yet."""
    try:
        profile = await service.update_profile(body.to_changes())
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProfileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ProfileRead.model_validate(profile)
