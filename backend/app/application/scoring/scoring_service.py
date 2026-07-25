"""Job scoring use case.

Loads a profile and a job, asks an `LLMProvider` to score their fit, and
persists the result via `JobMatchRepository`. No FastAPI, no SQLAlchemy,
no Anthropic SDK — only the `Protocol`s it depends on, exactly the shape
Milestone 0 (`docs/architecture/ai-architecture.md`) described for this
use case before any of the surrounding infrastructure existed.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.application.scoring.ports import JobMatchRepository, LLMProvider
from app.core.logging import get_logger
from app.domain.value_objects.match_result import MatchResult

if TYPE_CHECKING:
    from app.application.jobs.ports import JobRepository
    from app.infrastructure.db.models import JobMatch

logger = get_logger(__name__)


class JobNotFoundError(Exception):
    """Raised when scoring is requested against a job that doesn't exist."""


class ScoringResponseError(Exception):
    """Raised when the LLM provider's response can't be parsed into a
    valid `MatchResult` — a bad/garbled upstream response, not a business
    validation failure, so it's kept distinct from `ProfileValidationError`
    and friends. The API layer maps this to a 502.
    """


class _MatchResponseSchema(BaseModel):
    """The exact JSON shape the scoring prompt asks the model to return.

    This is the "structured output enforced via a Pydantic response
    schema" mechanism described in `docs/architecture/ai-architecture.md`
    — downstream code never parses free text from the model; it either
    gets a validated `_MatchResponseSchema` or a clear `ScoringResponseError`.
    """

    score: float = Field(ge=0, le=100)
    rationale: str = Field(min_length=1)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


_SYSTEM_PROMPT = """You are a career-matching assistant for CareerOS. You compare a \
candidate's profile against a job posting and produce an honest, specific compatibility \
assessment. Be direct about gaps — an overly generous score helps no one.

Respond with ONLY a single JSON object, no other text, matching exactly this shape:
{"score": <number 0-100>, "rationale": "<2-4 sentences explaining the score>", \
"matched_skills": ["<skill>", ...], "missing_skills": ["<skill>", ...]}"""


def _build_prompt(
    *, profile_summary: str, profile_skills: list[str], job_title: str, job_company: str, job_description: str
) -> str:
    skills_text = ", ".join(profile_skills) if profile_skills else "(none listed)"
    return (
        f"Candidate profile summary:\n{profile_summary or '(no summary provided)'}\n\n"
        f"Candidate skills: {skills_text}\n\n"
        f"Job: {job_title} at {job_company}\n\n"
        f"Job description:\n{job_description or '(no description provided)'}"
    )


class JobScoringService:
    """Orchestrates scoring the single profile against a job posting."""

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        profile_repository: ProfileRepository,
        job_repository: JobRepository,
        job_match_repository: JobMatchRepository,
    ) -> None:
        self._llm_provider = llm_provider
        self._profile_repository = profile_repository
        self._job_repository = job_repository
        self._job_match_repository = job_match_repository

    async def score_job(self, *, job_id: UUID) -> JobMatch:
        profile = await self._profile_repository.get()
        if profile is None:
            msg = "No profile has been created yet — create one before requesting a match."
            raise ProfileNotFoundError(msg)

        job = await self._job_repository.get_by_id(job_id=job_id)
        if job is None:
            msg = f"No job found with id={job_id}."
            raise JobNotFoundError(msg)

        prompt = _build_prompt(
            profile_summary=profile.summary or profile.headline or "",
            profile_skills=[skill.name for skill in profile.skills],
            job_title=job.title,
            job_company=job.company,
            job_description=job.description or "",
        )

        raw_response = await self._llm_provider.complete(
            system=_SYSTEM_PROMPT, prompt=prompt, response_format=_MatchResponseSchema
        )
        result = self._parse_response(raw_response)

        if profile.id is None:
            msg = "Persisted profile is missing an id — this should never happen."
            raise RuntimeError(msg)

        match = await self._job_match_repository.create(profile_id=profile.id, job=job, result=result)
        logger.info(
            "job_scored",
            profile_id=str(profile.id),
            job_id=str(job_id),
            score=str(result.score),
        )
        return match

    @staticmethod
    def _parse_response(raw_response: str) -> MatchResult:
        try:
            parsed = _MatchResponseSchema.model_validate_json(raw_response)
        except (ValidationError, json.JSONDecodeError) as exc:
            msg = f"LLM provider returned a response that couldn't be parsed as a match result: {raw_response!r}"
            raise ScoringResponseError(msg) from exc

        try:
            return MatchResult(
                score=Decimal(str(round(parsed.score, 2))),
                rationale=parsed.rationale,
                matched_skills=parsed.matched_skills,
                missing_skills=parsed.missing_skills,
            )
        except ValueError as exc:
            msg = f"LLM provider returned an invalid match result: {exc}"
            raise ScoringResponseError(msg) from exc
