"""API-level integration tests for the cover-letters endpoints.

Mirrors `test_resumes_api.py` — real app, real database, faked LLM
provider/PDF renderer/file storage.
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
    get_cover_letter_repository,
    get_file_storage,
    get_job_repository,
    get_llm_provider,
    get_pdf_renderer,
    get_profile_repository,
)
from app.core.config import get_settings
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.repositories.generated_cover_letter_repository import (
    SqlAlchemyGeneratedCoverLetterRepository,
)
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository
from app.main import create_app


class FakeLLMProvider:
    def __init__(self, response_text: str | None = None) -> None:
        self._response_text = response_text or json.dumps(
            {"body": "I would love to bring my skills to this role."}
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
    app.dependency_overrides[get_cover_letter_repository] = lambda: SqlAlchemyGeneratedCoverLetterRepository(
        db_session
    )
    app.dependency_overrides[get_llm_provider] = lambda: llm_provider or FakeLLMProvider()
    app.dependency_overrides[get_pdf_renderer] = lambda: FakePdfRenderer()
    app.dependency_overrides[get_file_storage] = lambda: shared_file_storage
    return app


@pytest.fixture
async def cover_letters_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
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
async def test_generate_cover_letter_succeeds(
    cover_letters_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(cover_letters_client)
    job_id = await _seed_job(db_session)

    response = await cover_letters_client.post(
        _prefix("cover-letters/generate"), json={"job_id": str(job_id)}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["body"] == "I would love to bring my skills to this role."


@pytest.mark.asyncio
async def test_generate_cover_letter_returns_404_when_no_profile_exists(
    cover_letters_client: AsyncClient, db_session: AsyncSession
) -> None:
    job_id = await _seed_job(db_session)

    response = await cover_letters_client.post(
        _prefix("cover-letters/generate"), json={"job_id": str(job_id)}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_cover_letter_returns_404_for_unknown_job(cover_letters_client: AsyncClient) -> None:
    await _create_profile(cover_letters_client)

    response = await cover_letters_client.post(
        _prefix("cover-letters/generate"), json={"job_id": str(uuid.uuid4())}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_cover_letter_rejects_missing_job_id(cover_letters_client: AsyncClient) -> None:
    await _create_profile(cover_letters_client)

    response = await cover_letters_client.post(_prefix("cover-letters/generate"), json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_cover_letters_returns_newest_first(
    cover_letters_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(cover_letters_client)
    job_one = await _seed_job(db_session, external_id="job-1")
    job_two = await _seed_job(db_session, external_id="job-2")

    await cover_letters_client.post(_prefix("cover-letters/generate"), json={"job_id": str(job_one)})
    await cover_letters_client.post(_prefix("cover-letters/generate"), json={"job_id": str(job_two)})

    response = await cover_letters_client.get(_prefix("cover-letters"))

    assert response.status_code == 200
    body = response.json()
    assert len(body["cover_letters"]) == 2
    assert body["cover_letters"][0]["job_id"] == str(job_two)


@pytest.mark.asyncio
async def test_download_cover_letter_returns_pdf_bytes(
    cover_letters_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_profile(cover_letters_client)
    job_id = await _seed_job(db_session)
    generate_response = await cover_letters_client.post(
        _prefix("cover-letters/generate"), json={"job_id": str(job_id)}
    )
    cover_letter_id = generate_response.json()["id"]

    response = await cover_letters_client.get(_prefix(f"cover-letters/{cover_letter_id}/download"))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-fake"


@pytest.mark.asyncio
async def test_download_unknown_cover_letter_returns_404(cover_letters_client: AsyncClient) -> None:
    await _create_profile(cover_letters_client)

    response = await cover_letters_client.get(_prefix(f"cover-letters/{uuid.uuid4()}/download"))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_cover_letter_returns_502_on_malformed_llm_response(db_session: AsyncSession) -> None:
    app = _build_app(db_session, llm_provider=FakeLLMProvider(response_text="not valid json"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _create_profile(client)
        job_id = await _seed_job(db_session)

        response = await client.post(_prefix("cover-letters/generate"), json={"job_id": str(job_id)})

    assert response.status_code == 502
