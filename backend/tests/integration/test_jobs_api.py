"""API-level integration tests for the jobs endpoints.

Exercises the real app (real routing, real Pydantic validation, real
database via `db_session`) with only the job *source* faked — an actual
network call to Adzuna has no place in this suite (and `api.adzuna.com`
isn't reachable from this environment regardless). The dependency
override used here (`get_job_source_adapter`) is exactly the seam
`app/api/deps.py` was built for.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_job_repository, get_job_source_adapter
from app.core.config import get_settings
from app.domain.value_objects.job_posting import NormalizedJobPosting
from app.infrastructure.db.repositories.job_repository import SqlAlchemyJobRepository
from app.main import create_app
from tests.unit.test_job_ingestion_service import FakeJobSourceAdapter


@pytest.fixture
async def jobs_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """An HTTP client for the real app, with the DB dependency pointed at
    the per-test transactional session and the job source faked.
    """
    app = create_app()
    app.dependency_overrides[get_job_repository] = lambda: SqlAlchemyJobRepository(db_session)
    app.dependency_overrides[get_job_source_adapter] = lambda: FakeJobSourceAdapter(
        [
            NormalizedJobPosting(
                source="adzuna",
                external_id="api-1",
                title="Cloud Support Engineer",
                company="Example Corp",
                location="Cape Town",
            ),
            NormalizedJobPosting(
                source="adzuna",
                external_id="api-2",
                title="Platform Engineer",
                company="Example Corp",
                location="Remote",
            ),
        ]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_ingest_then_list_returns_the_ingested_jobs(jobs_client: AsyncClient) -> None:
    settings = get_settings()

    ingest_response = await jobs_client.post(
        f"{settings.api_v1_prefix}/jobs/ingest",
        json={"query": "cloud engineer", "location": "Cape Town"},
    )
    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()
    assert ingest_body == {"fetched": 2, "created": 2, "skipped_duplicates": 0}

    list_response = await jobs_client.get(f"{settings.api_v1_prefix}/jobs")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert {job["external_id"] for job in list_body["jobs"]} == {"api-1", "api-2"}
    assert list_body["next_cursor"] is None


@pytest.mark.asyncio
async def test_ingesting_twice_dedupes_on_the_second_run(jobs_client: AsyncClient) -> None:
    settings = get_settings()
    payload = {"query": "cloud engineer"}

    first = await jobs_client.post(f"{settings.api_v1_prefix}/jobs/ingest", json=payload)
    assert first.json()["created"] == 2

    second = await jobs_client.post(f"{settings.api_v1_prefix}/jobs/ingest", json=payload)
    assert second.json() == {"fetched": 2, "created": 0, "skipped_duplicates": 2}


@pytest.mark.asyncio
async def test_ingest_rejects_empty_query(jobs_client: AsyncClient) -> None:
    settings = get_settings()

    response = await jobs_client.post(f"{settings.api_v1_prefix}/jobs/ingest", json={"query": ""})

    assert response.status_code == 422  # Pydantic min_length=1 validation failure


@pytest.mark.asyncio
async def test_list_jobs_rejects_malformed_cursor(jobs_client: AsyncClient) -> None:
    settings = get_settings()

    response = await jobs_client.get(f"{settings.api_v1_prefix}/jobs", params={"cursor": "not-a-real-cursor"})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_jobs_respects_limit(jobs_client: AsyncClient) -> None:
    settings = get_settings()
    await jobs_client.post(f"{settings.api_v1_prefix}/jobs/ingest", json={"query": "cloud engineer"})

    response = await jobs_client.get(f"{settings.api_v1_prefix}/jobs", params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 1
    assert body["next_cursor"] is not None
