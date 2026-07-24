"""API-level integration tests for the profile endpoints.

Exercises the real app end-to-end (real routing, real Pydantic
validation, real database via `db_session`) — matching the pattern
established for jobs in Milestone 3 (`test_jobs_api.py`).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_profile_repository
from app.core.config import get_settings
from app.infrastructure.db.repositories.profile_repository import SqlAlchemyProfileRepository
from app.main import create_app


@pytest.fixture
async def profile_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_profile_repository] = lambda: SqlAlchemyProfileRepository(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def _profile_prefix() -> str:
    return f"{get_settings().api_v1_prefix}/profile"


@pytest.mark.asyncio
async def test_get_profile_returns_404_when_none_exists(profile_client: AsyncClient) -> None:
    response = await profile_client.get(_profile_prefix())

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_then_get_profile(profile_client: AsyncClient) -> None:
    payload = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "years_experience": 5,
        "skills": ["Python", "Azure"],
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2020-01-01",
                "currently_working": True,
            }
        ],
        "education": [{"institution": "MIT", "qualification": "BSc", "start_year": 2016, "end_year": 2020}],
    }

    create_response = await profile_client.post(_profile_prefix(), json=payload)
    assert create_response.status_code == 201
    created_body = create_response.json()
    assert created_body["email"] == "ada@example.com"
    assert {s["name"] for s in created_body["skills"]} == {"Python", "Azure"}
    assert created_body["experience"][0]["company"] == "Acme"

    get_response = await profile_client.get(_profile_prefix())
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created_body["id"]


@pytest.mark.asyncio
async def test_create_profile_twice_returns_409(profile_client: AsyncClient) -> None:
    payload = {"full_name": "Ada Lovelace", "email": "ada@example.com"}
    first = await profile_client.post(_profile_prefix(), json=payload)
    assert first.status_code == 201

    second = await profile_client.post(
        _profile_prefix(), json={"full_name": "Someone Else", "email": "someone@example.com"}
    )

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_profile_rejects_invalid_email(profile_client: AsyncClient) -> None:
    response = await profile_client.post(
        _profile_prefix(), json={"full_name": "Ada Lovelace", "email": "not-an-email"}
    )

    assert response.status_code == 422
    assert "not a valid email" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_profile_rejects_blank_full_name(profile_client: AsyncClient) -> None:
    """Caught by FastAPI's own `min_length=1` constraint — the standard
    422 response FastAPI produces natively, no custom handling needed.
    """
    response = await profile_client.post(
        _profile_prefix(), json={"full_name": "", "email": "ada@example.com"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_rejects_negative_salary(profile_client: AsyncClient) -> None:
    response = await profile_client.post(
        _profile_prefix(),
        json={"full_name": "Ada Lovelace", "email": "ada@example.com", "salary_expectation": -100},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_rejects_duplicate_skills(profile_client: AsyncClient) -> None:
    response = await profile_client.post(
        _profile_prefix(),
        json={
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "skills": ["Python", "python"],
        },
    )

    assert response.status_code == 422
    assert "Duplicate skill" in response.json()["detail"]


@pytest.mark.asyncio
async def test_patch_profile_updates_only_given_fields(profile_client: AsyncClient) -> None:
    await profile_client.post(
        _profile_prefix(),
        json={"full_name": "Ada Lovelace", "email": "ada@example.com", "headline": "Old headline"},
    )

    patch_response = await profile_client.patch(_profile_prefix(), json={"headline": "New headline"})

    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["headline"] == "New headline"
    assert body["full_name"] == "Ada Lovelace"


@pytest.mark.asyncio
async def test_patch_profile_replaces_skills_list(profile_client: AsyncClient) -> None:
    await profile_client.post(
        _profile_prefix(),
        json={"full_name": "Ada Lovelace", "email": "ada@example.com", "skills": ["Python"]},
    )

    response = await profile_client.patch(_profile_prefix(), json={"skills": ["Go", "Rust"]})

    assert response.status_code == 200
    assert {s["name"] for s in response.json()["skills"]} == {"Go", "Rust"}


@pytest.mark.asyncio
async def test_patch_profile_returns_404_when_no_profile_exists(profile_client: AsyncClient) -> None:
    response = await profile_client.patch(_profile_prefix(), json={"headline": "New headline"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_profile_can_clear_a_nullable_field(profile_client: AsyncClient) -> None:
    await profile_client.post(
        _profile_prefix(),
        json={"full_name": "Ada Lovelace", "email": "ada@example.com", "headline": "Old headline"},
    )

    response = await profile_client.patch(_profile_prefix(), json={"headline": None})

    assert response.status_code == 200
    assert response.json()["headline"] is None
