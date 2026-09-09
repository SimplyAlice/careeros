"""SQLAlchemy ORM models.

Every model is imported here so that Base.metadata is fully populated
for Alembic migrations and test database creation.
"""

from __future__ import annotations

from app.infrastructure.db.models.action import ActionModel
from app.infrastructure.db.models.approval import ApprovalModel
from app.infrastructure.db.models.application import Application, ApplicationStatus
from app.infrastructure.db.models.audit_log import AuditLogModel
from app.infrastructure.db.models.candidate_profile import CandidateProfile
from app.infrastructure.db.models.education import Education
from app.infrastructure.db.models.event import EventModel
from app.infrastructure.db.models.experience import Experience
from app.infrastructure.db.models.generated_cover_letter import GeneratedCoverLetter
from app.infrastructure.db.models.generated_resume import GeneratedResume
from app.infrastructure.db.models.incident import IncidentModel
from app.infrastructure.db.models.job import Job
from app.infrastructure.db.models.job_match import JobMatch
from app.infrastructure.db.models.profile import Profile
from app.infrastructure.db.models.refresh_token import RefreshToken
from app.infrastructure.db.models.resume import Resume
from app.infrastructure.db.models.resume_metadata import ResumeMetadata
from app.infrastructure.db.models.service import ServiceModel
from app.infrastructure.db.models.skill import Skill
from app.infrastructure.db.models.user import User

__all__ = [
    "ActionModel",
    "ApprovalModel",
    "Application",
    "ApplicationStatus",
    "AuditLogModel",
    "CandidateProfile",
    "Education",
    "EventModel",
    "Experience",
    "GeneratedCoverLetter",
    "GeneratedResume",
    "IncidentModel",
    "Job",
    "JobMatch",
    "Profile",
    "RefreshToken",
    "Resume",
    "ResumeMetadata",
    "ServiceModel",
    "Skill",
    "User",
]