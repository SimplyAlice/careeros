"""Job ingestion use case.

Fetches postings from a `JobSourceAdapter`, and persists the ones that
aren't already known via a `JobRepository` — the orchestration logic
FR-1/FR-2 in `docs/architecture/system-design.md` describe. No FastAPI,
SQLAlchemy, or httpx imports here: this module only knows about the two
`Protocol`s it depends on, so it's testable with fakes and swappable to a
Celery task body without modification once Milestone 8 adds scheduling.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.jobs.ports import JobRepository, JobSourceAdapter
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """A summary of one ingestion run — returned to the caller (API
    response today; a Celery task result once Milestone 8 lands) and
    logged as a structured business-metric event (see
    `docs/architecture/observability.md` §4 — "jobs ingested / hour" is
    exactly the kind of metric this result feeds).
    """

    fetched: int
    created: int
    skipped_duplicates: int


class JobAlreadyExistsError(Exception):
    """Raised by a `JobRepository.create()` implementation when a database-level
    uniqueness constraint rejects the insert — translates an
    infrastructure-specific exception (e.g. SQLAlchemy's `IntegrityError`)
    into a vocabulary the application layer already understands, so this
    module has no SQLAlchemy import.
    """


class JobIngestionService:
    """Orchestrates fetching and persisting job postings from one source."""

    def __init__(self, *, source_adapter: JobSourceAdapter, repository: JobRepository) -> None:
        self._source_adapter = source_adapter
        self._repository = repository

    async def ingest(self, *, query: str, location: str | None = None, limit: int = 50) -> IngestionResult:
        """Fetch postings for `query`/`location` and persist the new ones.

        Deduplication happens in two layers, deliberately:

        1. Here: a `get_by_source_and_external_id` lookup before insert,
           which avoids an unnecessary failed-insert round trip for the
           common case (re-running ingestion for a query you've already
           run).
        2. At the database (`uq_jobs_source_external_id`, from Milestone
           2): the actual guarantee that holds even if two ingestion runs
           race for the same posting — `create()` surfaces that as a
           duplicate too, so a race never crashes the whole run, it just
           counts as skipped.
        """
        postings = await self._source_adapter.fetch_jobs(query=query, location=location, limit=limit)

        created = 0
        skipped = 0
        for posting in postings:
            existing = await self._repository.get_by_source_and_external_id(
                source=posting.source, external_id=posting.external_id
            )
            if existing is not None:
                skipped += 1
                continue

            try:
                await self._repository.create(posting)
            except JobAlreadyExistsError:
                # Caught here rather than left to propagate: a duplicate
                # discovered at insert time (e.g. a concurrent ingestion
                # run for an overlapping query) is an expected outcome of
                # ingestion, not a failure of it.
                skipped += 1
            else:
                created += 1

        result = IngestionResult(fetched=len(postings), created=created, skipped_duplicates=skipped)
        logger.info(
            "job_ingestion_completed",
            source_query=query,
            fetched=result.fetched,
            created=result.created,
            skipped_duplicates=result.skipped_duplicates,
        )
        return result
