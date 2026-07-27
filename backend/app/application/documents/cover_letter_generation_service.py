"""Cover letter generation use case.

Unlike resumes, a cover letter always targets a specific job (per
`docs/architecture/ai-architecture.md`: "grounded in company name, role,
and 2-3 explicit points... not generic filler") — `job_id` is required,
not optional.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from app.application.documents.errors import DocumentGenerationResponseError
from app.application.documents.ports import FileStorage, GeneratedCoverLetterRepository, PdfRenderer
from app.application.jobs.ports import JobRepository
from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.application.scoring.ports import LLMProvider
from app.application.scoring.scoring_service import JobNotFoundError
from app.core.logging import get_logger
from app.domain.value_objects.generated_document import CoverLetterContent

if TYPE_CHECKING:
    from app.infrastructure.db.models import GeneratedCoverLetter

logger = get_logger(__name__)


class _CoverLetterResponseSchema(BaseModel):
    """The exact JSON shape the cover-letter prompt asks the model to return."""

    body: str = Field(min_length=1)


_SYSTEM_PROMPT = """You are a professional cover-letter writer for CareerOS. You write the \
substantive body paragraphs of a cover letter (no greeting or sign-off — those are added \
separately) connecting a candidate's real skills and experience to a specific job. Reference \
the company name and 2-3 concrete points of fit. Never invent skills, employers, or experience \
the candidate did not already list.

Respond with ONLY a single JSON object, no other text, matching exactly this shape:
{"body": "<2-4 paragraphs, no greeting or sign-off>"}"""


def _build_prompt(
    *, profile_summary: str, profile_skills: list[str], job_title: str, job_company: str, job_description: str
) -> str:
    skills_text = ", ".join(profile_skills) if profile_skills else "(none listed)"
    return (
        f"Candidate summary: {profile_summary or '(none provided)'}\n\n"
        f"Candidate skills: {skills_text}\n\n"
        f"Job: {job_title} at {job_company}\n\n"
        f"Job description:\n{job_description or '(no description provided)'}"
    )


class CoverLetterGenerationService:
    """Orchestrates generating a cover letter for the single profile, for one job."""

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        pdf_renderer: PdfRenderer,
        file_storage: FileStorage,
        profile_repository: ProfileRepository,
        job_repository: JobRepository,
        cover_letter_repository: GeneratedCoverLetterRepository,
    ) -> None:
        self._llm_provider = llm_provider
        self._pdf_renderer = pdf_renderer
        self._file_storage = file_storage
        self._profile_repository = profile_repository
        self._job_repository = job_repository
        self._cover_letter_repository = cover_letter_repository

    async def generate_cover_letter(self, *, job_id: UUID) -> GeneratedCoverLetter:
        profile = await self._profile_repository.get()
        if profile is None:
            msg = "No profile has been created yet — create one before generating a cover letter."
            raise ProfileNotFoundError(msg)

        job = await self._job_repository.get_by_id(job_id=job_id)
        if job is None:
            msg = f"No job found with id={job_id}."
            raise JobNotFoundError(msg)

        prompt = _build_prompt(
            profile_summary=profile.summary or "",
            profile_skills=[skill.name for skill in profile.skills],
            job_title=job.title,
            job_company=job.company,
            job_description=job.description or "",
        )

        raw_response = await self._llm_provider.complete(
            system=_SYSTEM_PROMPT, prompt=prompt, response_format=_CoverLetterResponseSchema
        )
        content = self._parse_response(raw_response)

        pdf_bytes = self._pdf_renderer.render_cover_letter(profile=profile, job=job, content=content)
        filename = f"cover-letter-{profile.id}-{job_id}.pdf"
        file_path = self._file_storage.save(filename=filename, content=pdf_bytes)

        if profile.id is None:
            msg = "Persisted profile is missing an id — this should never happen."
            raise RuntimeError(msg)

        cover_letter = await self._cover_letter_repository.create(
            profile_id=profile.id, job=job, content=content, file_path=file_path
        )
        logger.info("cover_letter_generated", profile_id=str(profile.id), job_id=str(job_id))
        return cover_letter

    @staticmethod
    def _parse_response(raw_response: str) -> CoverLetterContent:
        try:
            parsed = _CoverLetterResponseSchema.model_validate_json(raw_response)
        except (ValidationError, json.JSONDecodeError) as exc:
            msg = (
                f"LLM provider returned a response that couldn't be parsed as cover letter "
                f"content: {raw_response!r}"
            )
            raise DocumentGenerationResponseError(msg) from exc

        try:
            return CoverLetterContent(body=parsed.body)
        except ValueError as exc:
            msg = f"LLM provider returned invalid cover letter content: {exc}"
            raise DocumentGenerationResponseError(msg) from exc
