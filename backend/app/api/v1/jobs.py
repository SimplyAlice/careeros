"""Jobs API — list ingested jobs, and trigger ingestion from a source.

Both endpoints are unauthenticated at this milestone (JWT auth lands in a
later milestone) — acceptable for now since there's no per-user data here
yet, only the shared `jobs` catalog.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_job_ingestion_service, get_job_repository
from app.application.jobs.ingestion_service import IngestionResult, JobIngestionService
from app.application.jobs.ports import JobRepository
from app.core.pagination import InvalidCursorError
from app.infrastructure.job_sources.adzuna import AdzunaNotConfiguredError

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobRead(BaseModel):
    """API representation of a `Job`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    company: str
    location: str | None
    description: str | None
    url: str | None


class JobListResponse(BaseModel):
    """A page of jobs, newest first."""

    jobs: list[JobRead]
    next_cursor: str | None = Field(
        default=None,
        description="Pass as `?cursor=...` to fetch the next page; null when there are no more results.",
    )


class JobIngestRequest(BaseModel):
    """What to search for when triggering ingestion."""

    query: str = Field(..., min_length=1, examples=["cloud engineer"])
    location: str | None = Field(default=None, examples=["Cape Town"])
    limit: int = Field(default=50, ge=1, le=50)


class JobIngestResponse(BaseModel):
    """Summary of one ingestion run."""

    fetched: int
    created: int
    skipped_duplicates: int

    @classmethod
    def from_result(cls, result: IngestionResult) -> JobIngestResponse:
        return cls(
            fetched=result.fetched,
            created=result.created,
            skipped_duplicates=result.skipped_duplicates,
        )


@router.get("", response_model=JobListResponse, summary="List ingested jobs")
async def list_jobs(
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    cursor: Annotated[
        str | None, Query(description="Opaque pagination cursor from a previous response.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobListResponse:
    """Return jobs newest-first, cursor-paginated per `docs/architecture/api-design.md`."""
    try:
        jobs, next_cursor = await repository.list_jobs(cursor=cursor, limit=limit)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return JobListResponse(jobs=[JobRead.model_validate(job) for job in jobs], next_cursor=next_cursor)


@router.post(
    "/ingest",
    response_model=JobIngestResponse,
    summary="Ingest jobs matching a query from the configured job source",
)
async def ingest_jobs(
    body: JobIngestRequest,
    ingestion_service: Annotated[JobIngestionService, Depends(get_job_ingestion_service)],
) -> JobIngestResponse:
    """Run job ingestion synchronously and return a summary.

    This runs in-request rather than as a background task — a deliberate,
    temporary simplification: Celery isn't wired up until Milestone 8, and
    a single-page Adzuna search (≤50 results) completes well within a
    normal request timeout. Once scheduled ingestion lands, this same
    `JobIngestionService.ingest()` call becomes a Celery task body without
    changing the service itself (see `docs/adr/0004-redis-celery.md`).
    """
    try:
        result = await ingestion_service.ingest(query=body.query, location=body.location, limit=body.limit)
    except AdzunaNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return JobIngestResponse.from_result(result)
