"""Adzuna job source adapter.

Implements `JobSourceAdapter` (see `app/application/jobs/ports.py`)
against Adzuna's public job search API — chosen as the first job source
per `docs/architecture/system-design.md` because it's a free, official,
ToS-compliant API (see `docs/adr/0009-human-in-the-loop-automation.md`
for the broader reasoning on preferring official APIs over scraping).

API reference: https://developer.adzuna.com/overview
"""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.domain.value_objects.job_posting import NormalizedJobPosting

ADZUNA_API_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaNotConfiguredError(Exception):
    """Raised when Adzuna credentials aren't set.

    A clear, specific exception rather than letting a missing-credential
    call fail deep inside an HTTP request with a confusing 401 — the API
    layer catches this and returns a clear 503 telling the operator
    exactly which environment variables to set (see `app/api/v1/jobs.py`).
    """


class AdzunaJobSourceAdapter:
    """Fetches job postings from the Adzuna API and normalizes them."""

    def __init__(self, settings: Settings) -> None:
        self._app_id = settings.adzuna_app_id
        self._app_key = settings.adzuna_app_key
        self._country = settings.adzuna_country

    async def fetch_jobs(
        self, *, query: str, location: str | None = None, limit: int = 50
    ) -> list[NormalizedJobPosting]:
        """Fetch postings matching `query` (and optionally `location`) from Adzuna."""
        if not self._app_id or not self._app_key:
            msg = "Adzuna credentials are not configured (ADZUNA_APP_ID / ADZUNA_APP_KEY)."
            raise AdzunaNotConfiguredError(msg)

        params: dict[str, str | int] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": min(limit, 50),  # Adzuna's own page-size ceiling
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        url = f"{ADZUNA_API_BASE_URL}/{self._country}/search/1"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        return [self._normalize(result) for result in payload.get("results", [])]

    @staticmethod
    def _normalize(result: dict[str, object]) -> NormalizedJobPosting:
        """Map one Adzuna API result object into our source-agnostic shape."""
        company = result.get("company")
        location = result.get("location")
        return NormalizedJobPosting(
            source="adzuna",
            external_id=str(result["id"]),
            title=str(result.get("title", "")).strip(),
            company=(
                str(company.get("display_name", "Unknown")).strip()
                if isinstance(company, dict)
                else "Unknown"
            ),
            location=str(location.get("display_name")).strip() if isinstance(location, dict) else None,
            description=str(result["description"]).strip() if result.get("description") else None,
            url=str(result["redirect_url"]) if result.get("redirect_url") else None,
        )
