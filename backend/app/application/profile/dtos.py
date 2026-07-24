"""DTOs for profile use cases.

Plain dataclasses, not Pydantic models — the application layer shouldn't
depend on the API layer's validation library. `api/v1/profile.py`'s
Pydantic request schemas are responsible for parsing raw JSON into these;
`Profile.__post_init__` (domain layer) is what actually enforces business
rules on the resulting data, run identically regardless of what produced
the DTO.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.domain.entities.profile import RemotePreference


@dataclass(slots=True)
class ExperienceInput:
    company: str
    title: str
    start_date: date
    end_date: date | None = None
    currently_working: bool = False
    description: str | None = None


@dataclass(slots=True)
class EducationInput:
    institution: str
    qualification: str
    start_year: int
    field_of_study: str | None = None
    end_year: int | None = None


@dataclass(slots=True)
class ProfileCreateData:
    """Everything needed to create the (one and only) profile."""

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
    skills: list[str] = field(default_factory=list)
    experience: list[ExperienceInput] = field(default_factory=list)
    education: list[EducationInput] = field(default_factory=list)
