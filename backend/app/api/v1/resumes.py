"""Resumes API — generate a tailored resume, list past ones, download the PDF.

Unauthenticated, per the same pre-auth scope as `profile`/`jobs`/`matches`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    get_file_storage,
    get_profile_repository,
    get_resume_generation_service,
    get_resume_repository,
)
from app.application.documents.errors import DocumentGenerationResponseError
from app.application.documents.ports import FileStorage, GeneratedResumeRepository
from app.application.documents.resume_generation_service import ResumeGenerationService
from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.application.scoring.scoring_service import JobNotFoundError
from app.core.pagination import InvalidCursorError
from app.infrastructure.ai_providers.anthropic_provider import AnthropicNotConfiguredError

router = APIRouter(prefix="/resumes", tags=["resumes"])


class GeneratedResumeRead(BaseModel):
    """API representation of a `GeneratedResume`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None
    professional_summary: str
    emphasized_skills: list[str]
    created_at: datetime


class GeneratedResumeListResponse(BaseModel):
    resumes: list[GeneratedResumeRead]
    next_cursor: str | None = Field(
        default=None,
        description="Pass as `?cursor=...` to fetch the next page; null when there are no more results.",
    )


class GenerateResumeRequest(BaseModel):
    job_id: uuid.UUID | None = Field(
        default=None, description="Tailor the resume to this job; omit for a general-purpose resume."
    )


async def _load_owned_profile(profile_repository: ProfileRepository) -> uuid.UUID:
    profile = await profile_repository.get()
    if profile is None or profile.id is None:
        msg = "No profile has been created yet."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return profile.id


@router.post(
    "/generate",
    response_model=GeneratedResumeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a tailored (or general) resume",
)
async def generate_resume(
    body: GenerateResumeRequest,
    service: Annotated[ResumeGenerationService, Depends(get_resume_generation_service)],
) -> GeneratedResumeRead:
    """Generate a new resume version. Every call creates a new versioned row."""
    try:
        resume = await service.generate_resume(job_id=body.job_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnthropicNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except DocumentGenerationResponseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return GeneratedResumeRead.model_validate(resume)


@router.get("", response_model=GeneratedResumeListResponse, summary="List generated resumes")
async def list_resumes(
    repository: Annotated[GeneratedResumeRepository, Depends(get_resume_repository)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    cursor: Annotated[
        str | None, Query(description="Opaque pagination cursor from a previous response.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GeneratedResumeListResponse:
    """Return generated resumes for the profile, newest first."""
    profile_id = await _load_owned_profile(profile_repository)

    try:
        resumes, next_cursor = await repository.list_for_profile(
            profile_id=profile_id, cursor=cursor, limit=limit
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return GeneratedResumeListResponse(
        resumes=[GeneratedResumeRead.model_validate(resume) for resume in resumes], next_cursor=next_cursor
    )


@router.get("/{resume_id}/download", summary="Download a generated resume PDF")
async def download_resume(
    resume_id: uuid.UUID,
    repository: Annotated[GeneratedResumeRepository, Depends(get_resume_repository)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
) -> Response:
    """Stream the rendered PDF for a specific generated resume.

    Scoped to the owning profile — `resume_id` alone isn't enough to
    retrieve a document; it must belong to the single local profile.
    """
    profile_id = await _load_owned_profile(profile_repository)

    resume = await repository.get_by_id(profile_id=profile_id, resume_id=resume_id)
    if resume is None:
        msg = f"No generated resume found with id={resume_id}."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    pdf_bytes = file_storage.read(path=resume.file_path)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="resume-{resume_id}.pdf"'},
    )
