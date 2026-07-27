"""Unit tests for `ResumeGenerationService`.

Fakes only — no database, no Anthropic SDK, no real PDF rendering —
matching the pattern established for `JobScoringService` (Milestone 5).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from app.application.documents.errors import DocumentGenerationResponseError
from app.application.documents.resume_generation_service import ResumeGenerationService
from app.application.profile.errors import ProfileNotFoundError
from app.application.scoring.scoring_service import JobNotFoundError
from app.domain.entities.profile import Profile, Skill


class FakeLLMProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_prompt: str | None = None

    async def complete(self, *, system: str, prompt: str, response_format: Any = None) -> str:
        del system, response_format
        self.last_prompt = prompt
        return self.response_text


class FakePdfRenderer:
    def __init__(self) -> None:
        self.render_resume_calls: list[dict[str, Any]] = []

    def render_resume(self, *, profile: Any, content: Any) -> bytes:
        self.render_resume_calls.append({"profile": profile, "content": content})
        return b"%PDF-fake-resume-bytes"

    def render_cover_letter(self, *, profile: Any, job: Any, content: Any) -> bytes:
        raise NotImplementedError


class FakeFileStorage:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    def save(self, *, filename: str, content: bytes) -> str:
        path = f"/fake/{filename}"
        self.saved[path] = content
        return path

    def read(self, *, path: str) -> bytes:
        return self.saved[path]


class FakeProfileRepository:
    def __init__(self, profile: Profile | None) -> None:
        self._profile = profile

    async def get(self) -> Profile | None:
        return self._profile

    async def create(self, profile: Profile) -> Profile:
        raise NotImplementedError

    async def update(self, profile: Profile) -> Profile:
        raise NotImplementedError


class FakeJob:
    def __init__(self, *, id_: uuid.UUID, title: str, description: str | None) -> None:
        self.id = id_
        self.title = title
        self.company = "Acme Corp"
        self.description = description


class FakeJobRepository:
    def __init__(self, jobs: dict[uuid.UUID, FakeJob]) -> None:
        self._jobs = jobs

    async def get_by_source_and_external_id(self, *, source: str, external_id: str) -> FakeJob | None:
        raise NotImplementedError

    async def get_by_id(self, *, job_id: uuid.UUID) -> FakeJob | None:
        return self._jobs.get(job_id)

    async def create(self, posting: Any) -> FakeJob:
        raise NotImplementedError

    async def list_jobs(self, *, cursor: str | None, limit: int) -> tuple[list[FakeJob], str | None]:
        raise NotImplementedError


class FakeResumeRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(
        self, *, profile_id: uuid.UUID, job_id: uuid.UUID | None, content: Any, file_path: str
    ) -> Any:
        record = {"profile_id": profile_id, "job_id": job_id, "content": content, "file_path": file_path}
        self.created.append(record)
        return record

    async def get_by_id(self, *, profile_id: uuid.UUID, resume_id: uuid.UUID) -> Any:
        raise NotImplementedError

    async def list_for_profile(
        self, *, profile_id: uuid.UUID, cursor: str | None, limit: int
    ) -> tuple[list[Any], str | None]:
        raise NotImplementedError


def _profile(**overrides: object) -> Profile:
    defaults: dict[str, object] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "id": uuid.uuid4(),
        "skills": [Skill(name="Python"), Skill(name="Azure")],
    }
    defaults.update(overrides)
    return Profile(**defaults)  # type: ignore[arg-type]


def _valid_llm_json(summary: str = "Experienced backend engineer.", skills: list[str] | None = None) -> str:
    return json.dumps({"professional_summary": summary, "emphasized_skills": skills or ["Python"]})


def _make_service(
    *,
    llm_provider: FakeLLMProvider,
    profile: Profile | None,
    jobs: dict[uuid.UUID, FakeJob] | None = None,
    resume_repository: FakeResumeRepository | None = None,
) -> tuple[ResumeGenerationService, FakePdfRenderer, FakeFileStorage, FakeResumeRepository]:
    pdf_renderer = FakePdfRenderer()
    file_storage = FakeFileStorage()
    resume_repository = resume_repository or FakeResumeRepository()
    service = ResumeGenerationService(
        llm_provider=llm_provider,
        pdf_renderer=pdf_renderer,
        file_storage=file_storage,
        profile_repository=FakeProfileRepository(profile),
        job_repository=FakeJobRepository(jobs or {}),
        resume_repository=resume_repository,
    )
    return service, pdf_renderer, file_storage, resume_repository


@pytest.mark.asyncio
async def test_generate_resume_raises_when_no_profile_exists() -> None:
    service, *_ = _make_service(llm_provider=FakeLLMProvider(_valid_llm_json()), profile=None)

    with pytest.raises(ProfileNotFoundError):
        await service.generate_resume(job_id=None)


@pytest.mark.asyncio
async def test_generate_resume_without_job_id_succeeds() -> None:
    profile = _profile()
    service, pdf_renderer, file_storage, resume_repository = _make_service(
        llm_provider=FakeLLMProvider(_valid_llm_json()), profile=profile
    )

    result = await service.generate_resume(job_id=None)

    assert len(resume_repository.created) == 1
    assert resume_repository.created[0]["job_id"] is None
    assert len(pdf_renderer.render_resume_calls) == 1
    assert result["content"].professional_summary == "Experienced backend engineer."
    assert file_storage.saved  # PDF bytes were actually saved


@pytest.mark.asyncio
async def test_generate_resume_raises_when_job_not_found() -> None:
    service, *_ = _make_service(llm_provider=FakeLLMProvider(_valid_llm_json()), profile=_profile(), jobs={})

    with pytest.raises(JobNotFoundError):
        await service.generate_resume(job_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_generate_resume_tailors_to_a_specific_job() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", description="Manage cloud infra.")
    llm_provider = FakeLLMProvider(_valid_llm_json())
    service, *_ = _make_service(llm_provider=llm_provider, profile=_profile(), jobs={job_id: job})

    await service.generate_resume(job_id=job_id)

    assert llm_provider.last_prompt is not None
    assert "Cloud Engineer" in llm_provider.last_prompt


@pytest.mark.asyncio
async def test_generate_resume_rejects_emphasized_skills_not_on_the_profile() -> None:
    llm_provider = FakeLLMProvider(
        _valid_llm_json(skills=["Kubernetes"])
    )  # not one of the profile's real skills
    service, *_ = _make_service(llm_provider=llm_provider, profile=_profile())

    with pytest.raises(DocumentGenerationResponseError, match="not present on the profile"):
        await service.generate_resume(job_id=None)


@pytest.mark.asyncio
async def test_generate_resume_rejects_malformed_llm_response() -> None:
    service, *_ = _make_service(llm_provider=FakeLLMProvider("not json"), profile=_profile())

    with pytest.raises(DocumentGenerationResponseError):
        await service.generate_resume(job_id=None)


@pytest.mark.asyncio
async def test_generate_resume_rejects_missing_summary() -> None:
    bad_json = json.dumps({"emphasized_skills": []})  # missing required "professional_summary"
    service, *_ = _make_service(llm_provider=FakeLLMProvider(bad_json), profile=_profile())

    with pytest.raises(DocumentGenerationResponseError):
        await service.generate_resume(job_id=None)
