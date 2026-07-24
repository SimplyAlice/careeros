"""Profile domain entities.

Unlike `Job`/`Application` (Milestones 2–3, where the ORM model doubles as
the domain model — a pragmatic choice appropriate to how little business
logic those entities carry), `Profile` and its children carry real
validation rules (duplicate-skill prevention, date/year consistency,
salary sanity), so this milestone introduces genuine domain entities,
separate from the ORM models in `app/infrastructure/db/models/profile.py`.
This is an *addition* to the architecture, not a retroactive change — Job
and Application remain exactly as they were.

These are plain dataclasses with no framework imports (no SQLAlchemy, no
Pydantic, no FastAPI): `ProfileRepository` (infrastructure) translates
between these and ORM rows; the API layer's Pydantic schemas translate
between these and HTTP JSON. Validation runs once, here, regardless of
which direction data is flowing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^[0-9+\-()\s]{7,32}$")

_MAX_SHORT_STR = 255
_MAX_SUMMARY_LEN = 5000
_MAX_YEARS_EXPERIENCE = 70
_MAX_SALARY_EXPECTATION = Decimal("100_000_000")
_MIN_EDUCATION_YEAR = 1950


class ProfileValidationError(ValueError):
    """Raised when profile data violates a business rule.

    A subclass of `ValueError` (not a bare custom exception) so it's
    naturally catchable as "this input was invalid" at the API boundary,
    which translates it into a 422/400 response.
    """


class DuplicateSkillError(ProfileValidationError):
    """Raised when a submitted skills list contains the same skill twice
    (case-insensitively) — see `Profile.replace_skills`.
    """


class RemotePreference(StrEnum):
    """A candidate's working-location preference."""

    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    FLEXIBLE = "flexible"


def _require_non_empty(value: str, *, field_name: str, max_length: int = _MAX_SHORT_STR) -> str:
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} is required."
        raise ProfileValidationError(msg)
    if len(stripped) > max_length:
        msg = f"{field_name} must be at most {max_length} characters."
        raise ProfileValidationError(msg)
    return stripped


def _validate_optional_str(
    value: str | None, *, field_name: str, max_length: int = _MAX_SHORT_STR
) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > max_length:
        msg = f"{field_name} must be at most {max_length} characters."
        raise ProfileValidationError(msg)
    return stripped


@dataclass(slots=True)
class Skill:
    """A single named skill belonging to a profile."""

    name: str
    id: UUID | None = None

    def __post_init__(self) -> None:
        self.name = _require_non_empty(self.name, field_name="Skill name", max_length=100)


@dataclass(slots=True)
class Experience:
    """A single work-experience entry."""

    company: str
    title: str
    start_date: date
    end_date: date | None = None
    currently_working: bool = False
    description: str | None = None
    id: UUID | None = None

    def __post_init__(self) -> None:
        self.company = _require_non_empty(self.company, field_name="Experience company")
        self.title = _require_non_empty(self.title, field_name="Experience title")
        self.description = _validate_optional_str(
            self.description, field_name="Experience description", max_length=_MAX_SUMMARY_LEN
        )
        if self.currently_working and self.end_date is not None:
            msg = "An experience entry marked as currently_working cannot have an end_date."
            raise ProfileValidationError(msg)
        if self.end_date is not None and self.end_date < self.start_date:
            msg = "Experience end_date cannot be before start_date."
            raise ProfileValidationError(msg)


@dataclass(slots=True)
class Education:
    """A single education entry."""

    institution: str
    qualification: str
    start_year: int
    field_of_study: str | None = None
    end_year: int | None = None
    id: UUID | None = None

    def __post_init__(self) -> None:
        self.institution = _require_non_empty(self.institution, field_name="Institution")
        self.qualification = _require_non_empty(self.qualification, field_name="Qualification")
        self.field_of_study = _validate_optional_str(self.field_of_study, field_name="Field of study")

        current_year = datetime.now(UTC).year
        if not (_MIN_EDUCATION_YEAR <= self.start_year <= current_year + 1):
            msg = f"start_year must be between {_MIN_EDUCATION_YEAR} and {current_year + 1}."
            raise ProfileValidationError(msg)
        if self.end_year is not None and self.end_year < self.start_year:
            msg = "end_year cannot be before start_year."
            raise ProfileValidationError(msg)


@dataclass(slots=True)
class ResumeMetadata:
    """Metadata about a resume file — no file content, per Milestone 4 scope
    (resume upload/storage is a later milestone; see `docs/adr/0012-profile-management.md`).
    """

    filename: str
    uploaded_at: datetime
    id: UUID | None = None

    def __post_init__(self) -> None:
        self.filename = _require_non_empty(self.filename, field_name="Resume filename", max_length=512)


@dataclass(slots=True)
class Profile:
    """The job seeker's professional profile — the single-profile aggregate
    root this milestone manages (see the ADR for why "single profile" is a
    deliberate, temporary scope, not a permanent limitation).
    """

    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    years_experience: int = 0
    preferred_job_title: str | None = None
    preferred_location: str | None = None
    salary_expectation: Decimal | None = None
    remote_preference: RemotePreference = RemotePreference.FLEXIBLE
    skills: list[Skill] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    resumes: list[ResumeMetadata] = field(default_factory=list)
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self._validate_core_fields()
        self._check_no_duplicate_skills(self.skills)

    def _validate_core_fields(self) -> None:
        self.full_name = _require_non_empty(self.full_name, field_name="Full name")

        email = self.email.strip()
        if not _EMAIL_PATTERN.match(email):
            msg = f"'{self.email}' is not a valid email address."
            raise ProfileValidationError(msg)
        self.email = email

        if self.phone is not None:
            phone = self.phone.strip()
            if phone and not _PHONE_PATTERN.match(phone):
                msg = "Phone number must be 7-32 characters and contain only digits, spaces, +, -, ( or )."
                raise ProfileValidationError(msg)
            self.phone = phone or None

        self.location = _validate_optional_str(self.location, field_name="Location")
        self.headline = _validate_optional_str(self.headline, field_name="Headline")
        self.summary = _validate_optional_str(self.summary, field_name="Summary", max_length=_MAX_SUMMARY_LEN)
        self.preferred_job_title = _validate_optional_str(
            self.preferred_job_title, field_name="Preferred job title"
        )
        self.preferred_location = _validate_optional_str(
            self.preferred_location, field_name="Preferred location"
        )

        if self.years_experience < 0 or self.years_experience > _MAX_YEARS_EXPERIENCE:
            msg = f"years_experience must be between 0 and {_MAX_YEARS_EXPERIENCE}."
            raise ProfileValidationError(msg)

        if self.salary_expectation is not None:
            if self.salary_expectation < 0:
                msg = "salary_expectation cannot be negative."
                raise ProfileValidationError(msg)
            if self.salary_expectation > _MAX_SALARY_EXPECTATION:
                msg = f"salary_expectation must be at most {_MAX_SALARY_EXPECTATION}."
                raise ProfileValidationError(msg)

    @staticmethod
    def _check_no_duplicate_skills(skills: list[Skill]) -> None:
        seen: set[str] = set()
        for skill in skills:
            key = skill.name.casefold()
            if key in seen:
                msg = f"Duplicate skill: '{skill.name}'."
                raise DuplicateSkillError(msg)
            seen.add(key)

    def replace_skills(self, skills: list[Skill]) -> None:
        """Wholesale-replace the skills list, rejecting case-insensitive duplicates."""
        self._check_no_duplicate_skills(skills)
        self.skills = skills

    def replace_experience(self, experience: list[Experience]) -> None:
        """Wholesale-replace the experience list.

        Each `Experience` already validated itself in `__post_init__`;
        nothing further to check across the list as a whole (unlike
        skills, overlapping employment dates are common and legitimate).
        """
        self.experience = experience

    def replace_education(self, education: list[Education]) -> None:
        """Wholesale-replace the education list."""
        self.education = education

    def apply_patch(self, changes: dict[str, Any]) -> None:
        """Apply a partial update (only the keys present in `changes`) and re-validate.

        `changes` is expected to already be filtered to "fields the client
        actually included in the request" (see `api/v1/profile.py`'s use of
        Pydantic's `model_dump(exclude_unset=True)`) — a key present with
        value `None` means "clear this field," a key absent means "leave
        unchanged," which is exactly what `exclude_unset` gives us for
        free without a manual sentinel value.
        """
        allowed_fields = {
            "full_name",
            "email",
            "phone",
            "location",
            "headline",
            "summary",
            "years_experience",
            "preferred_job_title",
            "preferred_location",
            "salary_expectation",
            "remote_preference",
        }
        unknown = set(changes) - allowed_fields
        if unknown:
            msg = f"Cannot patch unknown field(s): {sorted(unknown)}."
            raise ProfileValidationError(msg)

        for key, value in changes.items():
            setattr(self, key, value)

        self._validate_core_fields()
