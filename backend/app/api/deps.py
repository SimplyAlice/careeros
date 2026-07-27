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

from app.application.documents.cover_letter_generation_service import CoverLetterGenerationService
from app.application.documents.ports import (
    FileStorage,
    GeneratedCoverLetterRepository,
    GeneratedResumeRepository,
    PdfRenderer,
)
from app.application.documents.resume_generation_service import ResumeGenerationService
from app.application.jobs.ingestion_service import JobIngestionService
from app.application.jobs.ports import JobRepository, JobSourceAdapter
from app.application.profile.ports import ProfileRepository
from app.application.profile.profile_service import ProfileService
from app.application.scoring.ports import JobMatchRepository, LLMProvider
from app.application.scoring.scoring_service import JobScoringService
from app.core.config import Settings, get_settings
from app.infrastructure.ai_providers.anthropic_provider import AnthropicProvider
from app.infrastructure.cache.redis import get_redis_client
from app.infrastructure.db.repositories.generated_cover_letter_repository import (
    SqlAlchemyGeneratedCoverLetterRepository,
)
from app.infrastructure.db.repositories.generated_resume_repository import SqlAlchemyGeneratedResumeRepository
from app.infrastructure.db.repositories.job_match_repository import SqlAlchemyJobMatchRepository
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository
from app.infrastructure.db.session import get_db_session
from app.infrastructure.job_sources.adzuna import AdzunaJobSourceAdapter
from app.infrastructure.rendering.pdf_renderer import FpdfPdfRenderer
from app.infrastructure.storage.local_storage import LocalFileStorage


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


def get_llm_provider(settings: Annotated[Settings, Depends(get_settings)]) -> LLMProvider:
    """The active LLM provider.

    A single `Depends()` chokepoint — the same pattern as
    `get_job_source_adapter` — so adding an OpenAI/Gemini adapter later
    (per `docs/adr/0005-ai-provider-abstraction.md`) changes this function
    only.
    """
    return AnthropicProvider(settings)


def get_job_match_repository(session: Annotated[AsyncSession, Depends(get_db_session)]) -> JobMatchRepository:
    return SqlAlchemyJobMatchRepository(session)


def get_job_scoring_service(
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    job_match_repository: Annotated[JobMatchRepository, Depends(get_job_match_repository)],
) -> JobScoringService:
    return JobScoringService(
        llm_provider=llm_provider,
        profile_repository=profile_repository,
        job_repository=job_repository,
        job_match_repository=job_match_repository,
    )


def get_pdf_renderer() -> PdfRenderer:
    """The active PDF renderer.

    A single `Depends()` chokepoint, the same pattern as
    `get_job_source_adapter`/`get_llm_provider` — swapping rendering
    libraries later changes this function only.
    """
    return FpdfPdfRenderer()


def get_file_storage(settings: Annotated[Settings, Depends(get_settings)]) -> FileStorage:
    """The active file storage backend.

    A single `Depends()` chokepoint — swapping `LocalFileStorage` for an
    Azure Blob Storage adapter later (per
    `docs/architecture/cloud-architecture.md`) changes this function
    only.
    """
    return LocalFileStorage(settings.generated_documents_dir)


def get_resume_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> GeneratedResumeRepository:
    return SqlAlchemyGeneratedResumeRepository(session)


def get_cover_letter_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GeneratedCoverLetterRepository:
    return SqlAlchemyGeneratedCoverLetterRepository(session)


def get_resume_generation_service(
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    pdf_renderer: Annotated[PdfRenderer, Depends(get_pdf_renderer)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    resume_repository: Annotated[GeneratedResumeRepository, Depends(get_resume_repository)],
) -> ResumeGenerationService:
    return ResumeGenerationService(
        llm_provider=llm_provider,
        pdf_renderer=pdf_renderer,
        file_storage=file_storage,
        profile_repository=profile_repository,
        job_repository=job_repository,
        resume_repository=resume_repository,
    )


def get_cover_letter_generation_service(
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    pdf_renderer: Annotated[PdfRenderer, Depends(get_pdf_renderer)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    cover_letter_repository: Annotated[GeneratedCoverLetterRepository, Depends(get_cover_letter_repository)],
) -> CoverLetterGenerationService:
    return CoverLetterGenerationService(
        llm_provider=llm_provider,
        pdf_renderer=pdf_renderer,
        file_storage=file_storage,
        profile_repository=profile_repository,
        job_repository=job_repository,
        cover_letter_repository=cover_letter_repository,
    )


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
    "get_llm_provider",
    "get_job_match_repository",
    "get_job_scoring_service",
    "get_pdf_renderer",
    "get_file_storage",
    "get_resume_repository",
    "get_cover_letter_repository",
    "get_resume_generation_service",
    "get_cover_letter_generation_service",
]
