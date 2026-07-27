"""Cover letters API — generate a cover letter for a job, list past ones, download the PDF."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import (
    get_cover_letter_generation_service,
    get_cover_letter_repository,
    get_file_storage,
    get_profile_repository,
)
from app.application.documents.cover_letter_generation_service import CoverLetterGenerationService
from app.application.documents.errors import DocumentGenerationResponseError
from app.application.documents.ports import FileStorage, GeneratedCoverLetterRepository
from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.application.scoring.scoring_service import JobNotFoundError
from app.core.pagination import InvalidCursorError
from app.infrastructure.ai_providers.anthropic_provider import AnthropicNotConfiguredError

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


class GeneratedCoverLetterRead(BaseModel):
    """API representation of a `GeneratedCoverLetter`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    body: str
    created_at: datetime


class GeneratedCoverLetterListResponse(BaseModel):
    cover_letters: list[GeneratedCoverLetterRead]
    next_cursor: str | None = Field(
        default=None,
        description="Pass as `?cursor=...` to fetch the next page; null when there are no more results.",
    )


class GenerateCoverLetterRequest(BaseModel):
    job_id: uuid.UUID


async def _load_owned_profile(profile_repository: ProfileRepository) -> uuid.UUID:
    profile = await profile_repository.get()
    if profile is None or profile.id is None:
        msg = "No profile has been created yet."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return profile.id


@router.post(
    "/generate",
    response_model=GeneratedCoverLetterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a cover letter for a job",
)
async def generate_cover_letter(
    body: GenerateCoverLetterRequest,
    service: Annotated[CoverLetterGenerationService, Depends(get_cover_letter_generation_service)],
) -> GeneratedCoverLetterRead:
    """Generate a new cover letter version for the given job."""
    try:
        cover_letter = await service.generate_cover_letter(job_id=body.job_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnthropicNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except DocumentGenerationResponseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return GeneratedCoverLetterRead.model_validate(cover_letter)


@router.get("", response_model=GeneratedCoverLetterListResponse, summary="List generated cover letters")
async def list_cover_letters(
    repository: Annotated[GeneratedCoverLetterRepository, Depends(get_cover_letter_repository)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    cursor: Annotated[
        str | None, Query(description="Opaque pagination cursor from a previous response.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GeneratedCoverLetterListResponse:
    """Return generated cover letters for the profile, newest first."""
    profile_id = await _load_owned_profile(profile_repository)

    try:
        cover_letters, next_cursor = await repository.list_for_profile(
            profile_id=profile_id, cursor=cursor, limit=limit
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return GeneratedCoverLetterListResponse(
        cover_letters=[GeneratedCoverLetterRead.model_validate(cl) for cl in cover_letters],
        next_cursor=next_cursor,
    )


@router.get("/{cover_letter_id}/download", summary="Download a generated cover letter PDF")
async def download_cover_letter(
    cover_letter_id: uuid.UUID,
    repository: Annotated[GeneratedCoverLetterRepository, Depends(get_cover_letter_repository)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    file_storage: Annotated[FileStorage, Depends(get_file_storage)],
) -> Response:
    """Stream the rendered PDF for a specific generated cover letter."""
    profile_id = await _load_owned_profile(profile_repository)

    cover_letter = await repository.get_by_id(profile_id=profile_id, cover_letter_id=cover_letter_id)
    if cover_letter is None:
        msg = f"No generated cover letter found with id={cover_letter_id}."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    pdf_bytes = file_storage.read(path=cover_letter.file_path)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cover-letter-{cover_letter_id}.pdf"'},
    )
