"""Unit tests for `AdzunaJobSourceAdapter`.

HTTP is mocked by monkeypatching `httpx.AsyncClient.get` — this is a unit
test for our normalization/error-handling logic, not a contract test
against Adzuna's live API (which would be a separate, deliberately-labeled
integration test, run manually or on a schedule, not as part of the
regular suite — and `api.adzuna.com` isn't reachable from this sandboxed
environment regardless).
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.job_sources.adzuna import AdzunaJobSourceAdapter, AdzunaNotConfiguredError

ADZUNA_SAMPLE_RESPONSE = {
    "results": [
        {
            "id": 123456,
            "title": "  Senior Cloud Engineer  ",
            "company": {"display_name": "Example Corp"},
            "location": {"display_name": "Cape Town, South Africa"},
            "description": "Build and operate cloud infrastructure.",
            "redirect_url": "https://www.adzuna.com/details/123456",
        },
        {
            "id": 789012,
            "title": "Backend Developer",
            # Deliberately missing "company" and "location" to exercise
            # the adapter's fallback handling for incomplete API responses.
            "description": None,
        },
    ]
}


def _configured_settings() -> Settings:
    return Settings(
        secret_key="test",
        adzuna_app_id="test-app-id",
        adzuna_app_key="test-app-key",
        adzuna_country="gb",
    )


@pytest.mark.asyncio
async def test_fetch_jobs_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = AdzunaJobSourceAdapter(_configured_settings())

    async def fake_get(self: httpx.AsyncClient, url: str, params: dict[str, object]) -> httpx.Response:
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(200, json=ADZUNA_SAMPLE_RESPONSE, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    postings = await adapter.fetch_jobs(query="cloud engineer", location="Cape Town")

    assert len(postings) == 2

    first = postings[0]
    assert first.source == "adzuna"
    assert first.external_id == "123456"
    assert first.title == "Senior Cloud Engineer"  # whitespace stripped
    assert first.company == "Example Corp"
    assert first.location == "Cape Town, South Africa"
    assert first.url == "https://www.adzuna.com/details/123456"

    second = postings[1]
    assert second.external_id == "789012"
    assert second.company == "Unknown"  # missing "company" key handled gracefully
    assert second.location is None
    assert second.description is None


@pytest.mark.asyncio
async def test_fetch_jobs_raises_when_not_configured() -> None:
    unconfigured = Settings(secret_key="test")  # adzuna_app_id/app_key default to None
    adapter = AdzunaJobSourceAdapter(unconfigured)

    with pytest.raises(AdzunaNotConfiguredError):
        await adapter.fetch_jobs(query="cloud engineer")


@pytest.mark.asyncio
async def test_fetch_jobs_propagates_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = AdzunaJobSourceAdapter(_configured_settings())

    async def fake_get(self: httpx.AsyncClient, url: str, params: dict[str, object]) -> httpx.Response:
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(500, content=json.dumps({"error": "boom"}), request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.fetch_jobs(query="cloud engineer")
