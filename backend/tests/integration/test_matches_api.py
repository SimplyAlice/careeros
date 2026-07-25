"""API-level integration tests for the matches endpoints.

Exercises the real app end-to-end (real routing, real Pydantic
validation, real database) with only the LLM provider faked — matching
the pattern established for jobs (Milestone 3, faking the job source) and
profile (Milestone 4). Jobs are seeded directly via the job repository
against the shared test session rather than through `/jobs/ingest`,
since that endpoint depends on the Adzuna adapter, which isn't part of
what's under test here.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_job_match_repository,
    get_job_repository,
    get_llm_provider,
    get_profile_repository,
)
from app.core.config import get_settings
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.ai_providers.anthropic_provider import AnthropicNotConfiguredError
from app.infrastructure.db.repositories.job_match_repository import SqlAlchemyJobMatchRepository
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository
from app.main import create_app


class FakeLLMProvider:
    def __init__(self, response_text: str | None = None, *, raises_not_configured: bool = False) -> None:
        self._response_text = response_text or json.dumps(
            {
                "score": 82,
                "rationale": "Strong overlap in cloud skills.",
                "matched_skills": ["Python"],
                "missing_skills": ["Kubernetes"],
            }
        )
        self._raises_not_configured = raises_not_configured

    async def complete(self, *, system: str, prompt: str, response_format: Any = None) -> str:
        del system, prompt, response_format
        if self._raises_not_configured:
            msg = "Anthropic API key is not configured (ANTHROPIC_API_KEY)."
            raise AnthropicNotConfiguredError(msg)
        return self._response_text


def _prefix(resource: str) -> str:
    return f"{get_settings().api_v1_prefix}/{resource}"


def _build_app(db_session: AsyncSession, *, llm_provider: FakeLLMProvider) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_profile_repository] = lambda: SqlAlchemyProfileRepository(db_session)
    app.dependency_overrides[get_job_repository] = lambda: SqlAlchemyJobRepository(db_session)
    app.dependency_overrides[get_job_match_repository] = lambda: SqlAlchemyJobMatchRepository(db_session)
    app.dependency_overrides[get_llm_provider] = lambda: llm_provider
    return app


@pytest.fixture
async def matches_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app = _build_app(db_session, llm_provider=FakeLLMProvider())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def _create_profile(client: AsyncClient) -> None:
    response = await client.post(
        _prefix("profile"),
        json={"full_name": "Ada Lovelace", "email": "ada@example.com", "skills": ["Python"]},
    )
    assert response.status_code == 201


async def _seed_job(db_session: AsyncSession, *, external_id: str = "job-1") -> uuid.UUID:
    repository = SqlAlchemyJobRepository(db_session)
    job = await repository.create(
        NormalizedJobPosting(
            source="adzuna",
            external_id=external_id,
            title="Cloud Engineer",
            company="Acme Corp",
            description="Manage cloud infrastructure.",
        )
    )
    await db_session.flush()
    return job.id


@pytest.mark.asyncio
async def test_score_job_persists_and_returns_a_match(
    matches_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(matches_client)
    job_id = await _seed_job(db_session)

    response = await matches_client.post(_prefix("matches"), json={"job_id": str(job_id)})

    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["score"]) == Decimal("82")
    assert body["rationale"] == "Strong overlap in cloud skills."
    assert body["matched_skills"] == ["Python"]
    assert body["missing_skills"] == ["Kubernetes"]
    assert body["job"]["title"] == "Cloud Engineer"


@pytest.mark.asyncio
async def test_score_job_returns_404_when_no_profile_exists(
    matches_client: AsyncClient, db_session: AsyncSession
) -> None:
    job_id = await _seed_job(db_session)

    response = await matches_client.post(_prefix("matches"), json={"job_id": str(job_id)})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_score_job_returns_404_for_unknown_job(matches_client: AsyncClient) -> None:
    await _create_profile(matches_client)

    response = await matches_client.post(_prefix("matches"), json={"job_id": str(uuid.uuid4())})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_score_job_returns_503_when_llm_not_configured(db_session: AsyncSession) -> None:
    app = _build_app(db_session, llm_provider=FakeLLMProvider(raises_not_configured=True))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _create_profile(client)
        job_id = await _seed_job(db_session)

        response = await client.post(_prefix("matches"), json={"job_id": str(job_id)})

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_score_job_returns_502_on_malformed_llm_response(db_session: AsyncSession) -> None:
    app = _build_app(db_session, llm_provider=FakeLLMProvider(response_text="not valid json"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _create_profile(client)
        job_id = await _seed_job(db_session)

        response = await client.post(_prefix("matches"), json={"job_id": str(job_id)})

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_rescoring_the_same_job_creates_a_second_match(
    matches_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(matches_client)
    job_id = await _seed_job(db_session)

    first = await matches_client.post(_prefix("matches"), json={"job_id": str(job_id)})
    second = await matches_client.post(_prefix("matches"), json={"job_id": str(job_id)})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


@pytest.mark.asyncio
async def test_list_matches_returns_404_when_no_profile_exists(matches_client: AsyncClient) -> None:
    response = await matches_client.get(_prefix("matches"))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_matches_returns_scored_jobs_newest_first(
    matches_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(matches_client)
    job_one = await _seed_job(db_session, external_id="job-1")
    job_two = await _seed_job(db_session, external_id="job-2")

    await matches_client.post(_prefix("matches"), json={"job_id": str(job_one)})
    await matches_client.post(_prefix("matches"), json={"job_id": str(job_two)})

    response = await matches_client.get(_prefix("matches"))

    assert response.status_code == 200
    body = response.json()
    assert len(body["matches"]) == 2
    # Newest first: job_two was scored second.
    assert body["matches"][0]["job"]["id"] == str(job_two)


@pytest.mark.asyncio
async def test_score_job_rejects_missing_job_id(matches_client: AsyncClient) -> None:
    await _create_profile(matches_client)

    response = await matches_client.post(_prefix("matches"), json={})

    assert response.status_code == 422
