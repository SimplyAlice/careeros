"""Shared FastAPI dependencies.

A single place for cross-cutting dependencies that route handlers will
`Depends()` on. Kept deliberately thin at this milestone — it re-exports
the settings/DB/Redis dependencies already defined in their owning
modules, so route handlers only need one import path
(`app.api.deps`) regardless of which infrastructure module actually
implements a dependency. Authentication dependencies (`get_current_user`,
`require_role`) are added here in the milestone that implements JWT auth.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.jobs.ingestion_service import JobIngestionService
from app.application.jobs.ports import JobRepository, JobSourceAdapter
from app.application.profile.ports import ProfileRepository
from app.application.profile.profile_service import ProfileService
from app.core.config import Settings, get_settings
from app.infrastructure.cache.redis import get_redis_client
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository
from app.infrastructure.db.session import get_db_session
from app.infrastructure.job_sources.adzuna import AdzunaJobSourceAdapter


def get_job_source_adapter(settings: Annotated[Settings, Depends(get_settings)]) -> JobSourceAdapter:
    """The active job source adapter.

    A single `Depends()` chokepoint — swapping in a Greenhouse/Lever
    adapter later, or making the source configurable, changes this
    function only, not any route handler or the ingestion service.
    """
    return AdzunaJobSourceAdapter(settings)


def get_job_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> JobRepository:
    return SqlAlchemyJobRepository(session)


def get_job_ingestion_service(
    source_adapter: Annotated[JobSourceAdapter, Depends(get_job_source_adapter)],
    repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> JobIngestionService:
    return JobIngestionService(source_adapter=source_adapter, repository=repository)


def get_profile_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ProfileRepository:
    return SqlAlchemyProfileRepository(session)


def get_profile_service(
    repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
) -> ProfileService:
    return ProfileService(repository)


__all__ = [
    "Settings",
    "get_settings",
    "get_db_session",
    "get_redis_client",
    "get_job_source_adapter",
    "get_job_repository",
    "get_job_ingestion_service",
    "get_profile_repository",
    "get_profile_service",
]
