"""Resume generation use case.

Generates a tailored (or general, if no job is specified) resume: an AI
written professional summary and skill emphasis, combined with the
profile's real, unmodified experience and education — rendered to PDF and
persisted. No FastAPI, no SQLAlchemy, no fpdf2 — only the `Protocol`s it
depends on, the same shape established for scoring (Milestone 5).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from app.application.documents.errors import DocumentGenerationResponseError
from app.application.documents.ports import FileStorage, GeneratedResumeRepository, PdfRenderer
from app.application.jobs.ports import JobRepository
from app.application.profile.errors import ProfileNotFoundError
from app.application.profile.ports import ProfileRepository
from app.application.scoring.ports import LLMProvider
from app.application.scoring.scoring_service import JobNotFoundError
from app.core.logging import get_logger
from app.domain.value_objects.generated_document import TailoredResumeContent

if TYPE_CHECKING:
    from app.infrastructure.db.models import GeneratedResume

logger = get_logger(__name__)


class _ResumeResponseSchema(BaseModel):
    """The exact JSON shape the resume-generation prompt asks the model to return."""

    professional_summary: str = Field(min_length=1)
    emphasized_skills: list[str] = Field(default_factory=list)


_SYSTEM_PROMPT = """You are a professional resume writer for CareerOS. You write a concise, \
specific professional summary for a candidate, and select which of their EXISTING skills to \
emphasize for a given job. You NEVER invent skills, employers, titles, or experience the \
candidate did not already list — you only rephrase and prioritize what's real.

Respond with ONLY a single JSON object, no other text, matching exactly this shape:
{"professional_summary": "<2-4 sentences>", "emphasized_skills": ["<skill from the candidate's \
real list>", ...]}"""


def _build_prompt(
    *, profile_skills: list[str], profile_summary: str, job_title: str | None, job_description: str | None
) -> str:
    skills_text = ", ".join(profile_skills) if profile_skills else "(none listed)"
    if job_title:
        target = (
            f"Target role: {job_title}\n\nJob description:\n{job_description or '(no description provided)'}"
        )
    else:
        target = "No specific job targeted — write a strong general-purpose summary."
    return (
        f"Candidate's existing skills (only select from these): {skills_text}\n\n"
        f"Candidate's existing summary (if any): {profile_summary or '(none)'}\n\n"
        f"{target}"
    )


class ResumeGenerationService:
    """Orchestrates generating a tailored resume for the single profile."""

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        pdf_renderer: PdfRenderer,
        file_storage: FileStorage,
        profile_repository: ProfileRepository,
        job_repository: JobRepository,
        resume_repository: GeneratedResumeRepository,
    ) -> None:
        self._llm_provider = llm_provider
        self._pdf_renderer = pdf_renderer
        self._file_storage = file_storage
        self._profile_repository = profile_repository
        self._job_repository = job_repository
        self._resume_repository = resume_repository

    async def generate_resume(self, *, job_id: UUID | None) -> GeneratedResume:
        profile = await self._profile_repository.get()
        if profile is None:
            msg = "No profile has been created yet — create one before generating a resume."
            raise ProfileNotFoundError(msg)

        job = None
        if job_id is not None:
            job = await self._job_repository.get_by_id(job_id=job_id)
            if job is None:
                msg = f"No job found with id={job_id}."
                raise JobNotFoundError(msg)

        prompt = _build_prompt(
            profile_skills=[skill.name for skill in profile.skills],
            profile_summary=profile.summary or "",
            job_title=job.title if job else None,
            job_description=job.description if job else None,
        )

        raw_response = await self._llm_provider.complete(
            system=_SYSTEM_PROMPT, prompt=prompt, response_format=_ResumeResponseSchema
        )
        content = self._parse_response(raw_response, known_skills=[skill.name for skill in profile.skills])

        pdf_bytes = self._pdf_renderer.render_resume(profile=profile, content=content)
        filename = f"resume-{profile.id}-{job_id or 'general'}.pdf"
        file_path = self._file_storage.save(filename=filename, content=pdf_bytes)

        if profile.id is None:
            msg = "Persisted profile is missing an id — this should never happen."
            raise RuntimeError(msg)

        resume = await self._resume_repository.create(
            profile_id=profile.id, job_id=job_id, content=content, file_path=file_path
        )
        logger.info("resume_generated", profile_id=str(profile.id), job_id=str(job_id) if job_id else None)
        return resume

    @staticmethod
    def _parse_response(raw_response: str, *, known_skills: list[str]) -> TailoredResumeContent:
        try:
            parsed = _ResumeResponseSchema.model_validate_json(raw_response)
        except (ValidationError, json.JSONDecodeError) as exc:
            msg = f"LLM provider returned a response that couldn't be parsed as resume content: {raw_response!r}"
            raise DocumentGenerationResponseError(msg) from exc

        # Enforced here, not just by prompt instruction: emphasized skills
        # must be a subset of the candidate's real, existing skills — the
        # concrete guardrail against the AI inventing skills the candidate
        # doesn't have (see docs/adr/0014-resume-cover-letter-generation.md).
        known_lower = {skill.casefold() for skill in known_skills}
        invented = [skill for skill in parsed.emphasized_skills if skill.casefold() not in known_lower]
        if invented:
            msg = f"LLM provider emphasized skills not present on the profile: {invented}"
            raise DocumentGenerationResponseError(msg)

        try:
            return TailoredResumeContent(
                professional_summary=parsed.professional_summary,
                emphasized_skills=parsed.emphasized_skills,
            )
        except ValueError as exc:
            msg = f"LLM provider returned invalid resume content: {exc}"
            raise DocumentGenerationResponseError(msg) from exc
