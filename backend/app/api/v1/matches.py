"""Matches API — score the profile against a job, and list past matches.

Unauthenticated, per the same pre-auth scope as `profile` and `jobs`
(see `docs/adr/0012-profile-management.md`,
`docs/adr/0013-score-against-profile-not-user.md`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_job_match_repository, get_job_scoring_service, get_profile_repository
from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.application.scoring.ports import JobMatchRepository
from app.application.scoring.scoring_service import JobNotFoundError, JobScoringService, ScoringResponseError
from app.core.pagination import InvalidCursorError
from app.infrastructure.ai_providers.anthropic_provider import AnthropicNotConfiguredError

router = APIRouter(prefix="/matches", tags=["matches"])


class MatchJobSummary(BaseModel):
    """A condensed view of the job a match refers to — enough for a list
    view without requiring a second request to `/jobs`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company: str
    location: str | None


class MatchRead(BaseModel):
    """API representation of a `JobMatch`.

    `score`/`rationale` are aliased from the ORM column names
    (`match_score`/`reasoning`, unchanged since Milestone 2) to clearer
    API field names — `populate_by_name` plus `from_attributes` lets
    Pydantic read the ORM attributes by their real names while the JSON
    response uses the nicer public names.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    job: MatchJobSummary
    score: Decimal = Field(validation_alias="match_score", serialization_alias="score")
    rationale: str | None = Field(validation_alias="reasoning", serialization_alias="rationale")
    matched_skills: list[str]
    missing_skills: list[str]
    created_at: datetime


class MatchListResponse(BaseModel):
    """A page of matches, newest first."""

    matches: list[MatchRead]
    next_cursor: str | None = Field(
        default=None,
        description="Pass as `?cursor=...` to fetch the next page; null when there are no more results.",
    )


class ScoreJobRequest(BaseModel):
    job_id: uuid.UUID


@router.post(
    "",
    response_model=MatchRead,
    status_code=status.HTTP_201_CREATED,
    summary="Score the profile against a job",
)
async def score_job(
    body: ScoreJobRequest,
    service: Annotated[JobScoringService, Depends(get_job_scoring_service)],
) -> MatchRead:
    """Score the single local profile against the given job and persist the result.

    Every call creates a new `JobMatch` row — re-scoring the same job is
    allowed and expected (score history over time), not deduplicated.
    """
    try:
        match = await service.score_job(job_id=body.job_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnthropicNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ScoringResponseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return MatchRead.model_validate(match)


@router.get("", response_model=MatchListResponse, summary="List past matches for the profile")
async def list_matches(
    match_repository: Annotated[JobMatchRepository, Depends(get_job_match_repository)],
    profile_repository: Annotated[ProfileRepository, Depends(get_profile_repository)],
    cursor: Annotated[
        str | None, Query(description="Opaque pagination cursor from a previous response.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MatchListResponse:
    """Return past matches for the single local profile, newest first.

    404 if no profile has been created yet — there's nothing to have been
    matched against.
    """
    profile = await profile_repository.get()
    if profile is None or profile.id is None:
        msg = "No profile has been created yet."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    try:
        matches, next_cursor = await match_repository.list_for_profile(
            profile_id=profile.id, cursor=cursor, limit=limit
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return MatchListResponse(
        matches=[MatchRead.model_validate(match) for match in matches], next_cursor=next_cursor
    )
