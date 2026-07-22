"""Ports for job ingestion.

`JobIngestionService` (in `ingestion_service.py`) depends on these
`Protocol`s, not on any concrete implementation — the Strategy pattern
already established for AI providers (`docs/adr/0005-ai-provider-abstraction.md`)
applied here to job sources. `AdzunaJobSourceAdapter` (infrastructure layer)
implements `JobSourceAdapter` structurally; adding Greenhouse/Lever later
means writing a new adapter class, not touching this service.

`JobRepository` is intentionally a narrow Protocol — only the methods the
ingestion service and the `/jobs` listing endpoint actually need — rather
than a generic repository interface. A wider interface would just be
unused surface area at this milestone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.domain.value_objects.job_posting import NormalizedJobPosting

if TYPE_CHECKING:
    from app.infrastructure.db.models import Job


class JobSourceAdapter(Protocol):
    """A source of job postings (Adzuna, and later Greenhouse/Lever)."""

    async def fetch_jobs(
        self, *, query: str, location: str | None = None, limit: int = 50
    ) -> list[NormalizedJobPosting]:
        """Fetch postings matching `query` (and optionally `location`).

        Returns already-normalized postings — the adapter is responsible
        for translating its provider's response shape, not the caller.
        """
        ...


class JobRepository(Protocol):
    """Persistence operations `JobIngestionService` and the jobs API need."""

    async def get_by_source_and_external_id(self, *, source: str, external_id: str) -> Job | None:
        """Look up a job already ingested from this source, if any."""
        ...

    async def create(self, posting: NormalizedJobPosting) -> Job:
        """Persist a new job posting."""
        ...

    async def list_jobs(self, *, cursor: str | None, limit: int) -> tuple[list[Job], str | None]:
        """Return a page of jobs (newest first) and the cursor for the next page.

        Returns `(jobs, next_cursor)` — `next_cursor` is `None` when there
        are no further pages.
        """
        ...
