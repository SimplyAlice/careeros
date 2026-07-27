"""API-level integration tests for the resumes endpoints.

Real app, real routing, real database — only the LLM provider, PDF
renderer, and file storage are faked (no real Anthropic call, no real
disk write needed for this suite), matching the pattern established for
matches (Milestone 5).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_file_storage,
    get_job_repository,
    get_llm_provider,
    get_pdf_renderer,
    get_profile_repository,
    get_resume_repository,
)
from app.core.config import get_settings
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.repositories.generated_resume_repository import SqlAlchemyGeneratedResumeRepository
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository
from app.main import create_app


class FakeLLMProvider:
    def __init__(self, response_text: str | None = None) -> None:
        self._response_text = response_text or json.dumps(
            {"professional_summary": "Strong cloud engineer.", "emphasized_skills": ["Python"]}
        )

    async def complete(self, *, system: str, prompt: str, response_format: Any = None) -> str:
        del system, prompt, response_format
        return self._response_text


class FakePdfRenderer:
    def render_resume(self, *, profile: Any, content: Any) -> bytes:
        return b"%PDF-fake"

    def render_cover_letter(self, *, profile: Any, job: Any, content: Any) -> bytes:
        return b"%PDF-fake"


class FakeFileStorage:
    def __init__(self) -> None:
        self._saved: dict[str, bytes] = {}

    def save(self, *, filename: str, content: bytes) -> str:
        path = f"/fake/{filename}"
        self._saved[path] = content
        return path

    def read(self, *, path: str) -> bytes:
        return self._saved[path]


def _prefix(resource: str) -> str:
    return f"{get_settings().api_v1_prefix}/{resource}"


def _build_app(db_session: AsyncSession, *, llm_provider: FakeLLMProvider | None = None) -> FastAPI:
    app = create_app()
    shared_file_storage = FakeFileStorage()
    app.dependency_overrides[get_profile_repository] = lambda: SqlAlchemyProfileRepository(db_session)
    app.dependency_overrides[get_job_repository] = lambda: SqlAlchemyJobRepository(db_session)
    app.dependency_overrides[get_resume_repository] = lambda: SqlAlchemyGeneratedResumeRepository(db_session)
    app.dependency_overrides[get_llm_provider] = lambda: llm_provider or FakeLLMProvider()
    app.dependency_overrides[get_pdf_renderer] = lambda: FakePdfRenderer()
    app.dependency_overrides[get_file_storage] = lambda: shared_file_storage
    return app


@pytest.fixture
async def resumes_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app = _build_app(db_session)
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
    job = await SqlAlchemyJobRepository(db_session).create(
        NormalizedJobPosting(source="adzuna", external_id=external_id, title="Cloud Engineer", company="Acme")
    )
    await db_session.flush()
    return job.id


@pytest.mark.asyncio
async def test_generate_resume_without_job_id_returns_a_general_resume(resumes_client: AsyncClient) -> None:
    await _create_profile(resumes_client)

    response = await resumes_client.post(_prefix("resumes/generate"), json={})

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] is None
    assert body["professional_summary"] == "Strong cloud engineer."
    assert body["emphasized_skills"] == ["Python"]


@pytest.mark.asyncio
async def test_generate_resume_returns_404_when_no_profile_exists(resumes_client: AsyncClient) -> None:
    response = await resumes_client.post(_prefix("resumes/generate"), json={})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_resume_tailored_to_a_job(
    resumes_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(resumes_client)
    job_id = await _seed_job(db_session)

    response = await resumes_client.post(_prefix("resumes/generate"), json={"job_id": str(job_id)})

    assert response.status_code == 201
    assert response.json()["job_id"] == str(job_id)


@pytest.mark.asyncio
async def test_generate_resume_returns_404_for_unknown_job(resumes_client: AsyncClient) -> None:
    await _create_profile(resumes_client)

    response = await resumes_client.post(_prefix("resumes/generate"), json={"job_id": str(uuid.uuid4())})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_resumes_returns_generated_resumes_newest_first(
    resumes_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(resumes_client)
    await resumes_client.post(_prefix("resumes/generate"), json={})
    await resumes_client.post(_prefix("resumes/generate"), json={})

    response = await resumes_client.get(_prefix("resumes"))

    assert response.status_code == 200
    assert len(response.json()["resumes"]) == 2


@pytest.mark.asyncio
async def test_download_resume_returns_pdf_bytes(resumes_client: AsyncClient) -> None:
    await _create_profile(resumes_client)
    generate_response = await resumes_client.post(_prefix("resumes/generate"), json={})
    resume_id = generate_response.json()["id"]

    response = await resumes_client.get(_prefix(f"resumes/{resume_id}/download"))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-fake"


@pytest.mark.asyncio
async def test_download_unknown_resume_returns_404(resumes_client: AsyncClient) -> None:
    await _create_profile(resumes_client)

    response = await resumes_client.get(_prefix(f"resumes/{uuid.uuid4()}/download"))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_resume_returns_502_on_malformed_llm_response(db_session: AsyncSession) -> None:
    app = _build_app(db_session, llm_provider=FakeLLMProvider(response_text="not valid json"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _create_profile(client)
        response = await client.post(_prefix("resumes/generate"), json={})

    assert response.status_code == 502
