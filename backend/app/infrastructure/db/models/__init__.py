"""SQLAlchemy ORM models.

Every model is imported here so that:

1. `Base.metadata` is fully populated as soon as this package is imported
   — required for Alembic's `--autogenerate` to see every table, and for
   `Base.metadata.create_all()` to create every table in tests.
2. Other layers (repositories, services, tests) have one stable import
   path (`from app.infrastructure.db.models import User`) regardless of
   which module a model actually lives in.

Import order matters only in that every model referenced by a
`TYPE_CHECKING`-only relationship type hint must be resolvable — since
those hints are all forward references (`from __future__ import annotations`)
resolved lazily by SQLAlchemy at mapper-configuration time, plain
alphabetical import order here is sufficient.
"""

from __future__ import annotations

from app.infrastructure.db.models.application import Application, ApplicationStatus
from app.infrastructure.db.models.candidate_profile import CandidateProfile
from app.infrastructure.db.models.education import Education
from app.infrastructure.db.models.experience import Experience
from app.infrastructure.db.models.generated_cover_letter import GeneratedCoverLetter
from app.infrastructure.db.models.generated_resume import GeneratedResume
from app.infrastructure.db.models.job import Job
from app.infrastructure.db.models.job_match import JobMatch
from app.infrastructure.db.models.profile import Profile
from app.infrastructure.db.models.resume import Resume
from app.infrastructure.db.models.resume_metadata import ResumeMetadata
from app.infrastructure.db.models.skill import Skill
from app.infrastructure.db.models.user import User

__all__ = [
    "Application",
    "ApplicationStatus",
    "CandidateProfile",
    "Education",
    "Experience",
    "GeneratedCoverLetter",
    "GeneratedResume",
    "Job",
    "JobMatch",
    "Profile",
    "Resume",
    "ResumeMetadata",
    "Skill",
    "User",
]
