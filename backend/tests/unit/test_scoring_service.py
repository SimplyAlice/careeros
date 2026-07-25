"""Unit tests for `JobScoringService`.

Fakes only — no database, no Anthropic SDK — matching the pattern
established for `JobIngestionService` (Milestone 3) and `ProfileService`
(Milestone 4).
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.profile.errors import ProfileNotFoundError
from app.application.scoring.scoring_service import (
    JobNotFoundError,
    JobScoringService,
    ScoringResponseError,
)
from app.domain.entities.profile import Profile, Skill
from app.domain.value_objects.match_result import MatchResult


class FakeLLMProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_system: str | None = None
        self.last_prompt: str | None = None

    async def complete(self, *, system: str, prompt: str, response_format: Any = None) -> str:
        del response_format
        self.last_system = system
        self.last_prompt = prompt
        return self.response_text


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
    def __init__(self, *, id_: uuid.UUID, title: str, company: str, description: str | None) -> None:
        self.id = id_
        self.title = title
        self.company = company
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


class FakeJobMatchRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, *, profile_id: uuid.UUID, job: FakeJob, result: MatchResult) -> SimpleNamespace:
        record = {"profile_id": profile_id, "job": job, "result": result}
        self.created.append(record)
        return SimpleNamespace(
            id=uuid.uuid4(),
            profile_id=profile_id,
            job_id=job.id,
            match_score=result.score,
            reasoning=result.rationale,
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
        )

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


def _valid_llm_json(score: float = 82, rationale: str = "Strong overlap in cloud skills.") -> str:
    return json.dumps(
        {
            "score": score,
            "rationale": rationale,
            "matched_skills": ["Python", "Azure"],
            "missing_skills": ["Kubernetes"],
        }
    )


@pytest.mark.asyncio
async def test_score_job_raises_when_no_profile_exists() -> None:
    job_id = uuid.uuid4()
    service = JobScoringService(
        llm_provider=FakeLLMProvider(_valid_llm_json()),
        profile_repository=FakeProfileRepository(None),
        job_repository=FakeJobRepository({}),
        job_match_repository=FakeJobMatchRepository(),
    )

    with pytest.raises(ProfileNotFoundError):
        await service.score_job(job_id=job_id)


@pytest.mark.asyncio
async def test_score_job_raises_when_job_not_found() -> None:
    service = JobScoringService(
        llm_provider=FakeLLMProvider(_valid_llm_json()),
        profile_repository=FakeProfileRepository(_profile()),
        job_repository=FakeJobRepository({}),
        job_match_repository=FakeJobMatchRepository(),
    )

    with pytest.raises(JobNotFoundError):
        await service.score_job(job_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_score_job_persists_a_valid_result() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", company="Acme", description="Manage cloud infra.")
    match_repository = FakeJobMatchRepository()
    profile = _profile()

    service = JobScoringService(
        llm_provider=FakeLLMProvider(_valid_llm_json(score=82)),
        profile_repository=FakeProfileRepository(profile),
        job_repository=FakeJobRepository({job_id: job}),
        job_match_repository=match_repository,
    )

    match = await service.score_job(job_id=job_id)

    assert match.match_score == Decimal("82")
    assert match.matched_skills == ["Python", "Azure"]
    assert match.missing_skills == ["Kubernetes"]
    assert len(match_repository.created) == 1
    assert match_repository.created[0]["profile_id"] == profile.id


@pytest.mark.asyncio
async def test_score_job_includes_profile_skills_and_job_details_in_the_prompt() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", company="Acme", description="Manage cloud infra.")
    provider = FakeLLMProvider(_valid_llm_json())

    service = JobScoringService(
        llm_provider=provider,
        profile_repository=FakeProfileRepository(_profile()),
        job_repository=FakeJobRepository({job_id: job}),
        job_match_repository=FakeJobMatchRepository(),
    )

    await service.score_job(job_id=job_id)

    assert provider.last_prompt is not None
    assert "Python" in provider.last_prompt
    assert "Cloud Engineer" in provider.last_prompt
    assert "Acme" in provider.last_prompt


@pytest.mark.asyncio
async def test_score_job_raises_scoring_response_error_on_malformed_json() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", company="Acme", description=None)

    service = JobScoringService(
        llm_provider=FakeLLMProvider("this is not json"),
        profile_repository=FakeProfileRepository(_profile()),
        job_repository=FakeJobRepository({job_id: job}),
        job_match_repository=FakeJobMatchRepository(),
    )

    with pytest.raises(ScoringResponseError):
        await service.score_job(job_id=job_id)


@pytest.mark.asyncio
async def test_score_job_raises_scoring_response_error_on_out_of_range_score() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", company="Acme", description=None)
    bad_json = json.dumps({"score": 150, "rationale": "Great fit!"})

    service = JobScoringService(
        llm_provider=FakeLLMProvider(bad_json),
        profile_repository=FakeProfileRepository(_profile()),
        job_repository=FakeJobRepository({job_id: job}),
        job_match_repository=FakeJobMatchRepository(),
    )

    with pytest.raises(ScoringResponseError):
        await service.score_job(job_id=job_id)


@pytest.mark.asyncio
async def test_score_job_raises_scoring_response_error_on_missing_rationale() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", company="Acme", description=None)
    bad_json = json.dumps({"score": 50})  # missing required "rationale"

    service = JobScoringService(
        llm_provider=FakeLLMProvider(bad_json),
        profile_repository=FakeProfileRepository(_profile()),
        job_repository=FakeJobRepository({job_id: job}),
        job_match_repository=FakeJobMatchRepository(),
    )

    with pytest.raises(ScoringResponseError):
        await service.score_job(job_id=job_id)


@pytest.mark.asyncio
async def test_score_job_uses_headline_when_no_summary_is_set() -> None:
    job_id = uuid.uuid4()
    job = FakeJob(id_=job_id, title="Cloud Engineer", company="Acme", description=None)
    provider = FakeLLMProvider(_valid_llm_json())
    profile = _profile(summary=None, headline="Cloud-focused backend engineer")

    service = JobScoringService(
        llm_provider=provider,
        profile_repository=FakeProfileRepository(profile),
        job_repository=FakeJobRepository({job_id: job}),
        job_match_repository=FakeJobMatchRepository(),
    )

    await service.score_job(job_id=job_id)

    assert provider.last_prompt is not None
    assert "Cloud-focused backend engineer" in provider.last_prompt
