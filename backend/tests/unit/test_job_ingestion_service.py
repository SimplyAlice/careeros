"""Unit tests for `JobIngestionService`.

Uses hand-written fakes for both ports (`JobSourceAdapter`, `JobRepository`)
rather than a mocking framework — the ports are small enough that fakes
are clearer than mock-and-assert-call-args, and a fake genuinely behaves
like a real (if trivial) implementation, which catches more than a mock
would (e.g. the dedup-lookup-then-create sequencing).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.application.jobs.ingestion_service import JobAlreadyExistsError, JobIngestionService
from app.domain.value_objects.job_posting import NormalizedJobPosting


class FakeJobSourceAdapter:
    def __init__(self, postings: list[NormalizedJobPosting]) -> None:
        self._postings = postings
        self.last_query: str | None = None
        self.last_location: str | None = None

    async def fetch_jobs(
        self, *, query: str, location: str | None = None, limit: int = 50
    ) -> list[NormalizedJobPosting]:
        self.last_query = query
        self.last_location = location
        return self._postings


@dataclass
class _StoredJob:
    source: str
    external_id: str


@dataclass
class FakeJobRepository:
    """An in-memory stand-in for `JobRepository`.

    `existing` seeds postings that should be treated as already-ingested
    (dedup path); `fail_on` simulates a race condition where the database
    constraint rejects an insert the in-memory pre-check didn't catch.
    """

    existing: list[NormalizedJobPosting] = field(default_factory=list)
    fail_on: set[tuple[str, str]] = field(default_factory=set)
    created: list[NormalizedJobPosting] = field(default_factory=list)

    async def get_by_source_and_external_id(self, *, source: str, external_id: str) -> _StoredJob | None:
        for posting in self.existing:
            if posting.source == source and posting.external_id == external_id:
                return _StoredJob(source=source, external_id=external_id)
        return None

    async def create(self, posting: NormalizedJobPosting) -> _StoredJob:
        if (posting.source, posting.external_id) in self.fail_on:
            msg = "duplicate"
            raise JobAlreadyExistsError(msg)
        self.created.append(posting)
        return _StoredJob(source=posting.source, external_id=posting.external_id)

    async def list_jobs(self, *, cursor: str | None, limit: int) -> tuple[list[_StoredJob], str | None]:
        raise NotImplementedError  # not exercised by ingestion tests


def _posting(external_id: str, title: str = "Cloud Engineer") -> NormalizedJobPosting:
    return NormalizedJobPosting(
        source="adzuna",
        external_id=external_id,
        title=title,
        company="Example Corp",
    )


@pytest.mark.asyncio
async def test_ingest_creates_new_postings() -> None:
    adapter = FakeJobSourceAdapter([_posting("1"), _posting("2")])
    repository = FakeJobRepository()
    service = JobIngestionService(source_adapter=adapter, repository=repository)

    result = await service.ingest(query="cloud engineer", location="Remote")

    assert result.fetched == 2
    assert result.created == 2
    assert result.skipped_duplicates == 0
    assert len(repository.created) == 2
    assert adapter.last_query == "cloud engineer"
    assert adapter.last_location == "Remote"


@pytest.mark.asyncio
async def test_ingest_skips_postings_already_known_to_the_repository() -> None:
    already_known = _posting("1")
    adapter = FakeJobSourceAdapter([already_known, _posting("2")])
    repository = FakeJobRepository(existing=[already_known])
    service = JobIngestionService(source_adapter=adapter, repository=repository)

    result = await service.ingest(query="cloud engineer")

    assert result.fetched == 2
    assert result.created == 1
    assert result.skipped_duplicates == 1
    assert [p.external_id for p in repository.created] == ["2"]


@pytest.mark.asyncio
async def test_ingest_counts_a_racing_duplicate_as_skipped_not_a_failure() -> None:
    """The pre-check (`get_by_source_and_external_id`) can't see a row
    inserted by a concurrent ingestion run after the check but before this
    run's insert — the repository surfaces that as `JobAlreadyExistsError`,
    and the service must treat it the same as a dedup skip, not let it
    blow up the whole ingestion run.
    """
    racing_posting = _posting("1")
    adapter = FakeJobSourceAdapter([racing_posting])
    repository = FakeJobRepository(fail_on={("adzuna", "1")})
    service = JobIngestionService(source_adapter=adapter, repository=repository)

    result = await service.ingest(query="cloud engineer")

    assert result.created == 0
    assert result.skipped_duplicates == 1


@pytest.mark.asyncio
async def test_ingest_with_no_results_is_a_no_op() -> None:
    adapter = FakeJobSourceAdapter([])
    repository = FakeJobRepository()
    service = JobIngestionService(source_adapter=adapter, repository=repository)

    result = await service.ingest(query="a query that matches nothing")

    assert result.fetched == 0
    assert result.created == 0
    assert result.skipped_duplicates == 0
