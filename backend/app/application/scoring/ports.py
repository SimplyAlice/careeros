"""Ports for job scoring.

`JobScoringService` depends on these `Protocol`s, not on the Anthropic SDK
or SQLAlchemy — the same Strategy-pattern separation established for job
sources (`app/application/jobs/ports.py`, Milestone 3) and documented as
the intended shape for AI providers back in
`docs/adr/0005-ai-provider-abstraction.md` (Milestone 0). This milestone
is simply where that documented interface gets its first real
implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

from app.domain.value_objects.match_result import MatchResult

if TYPE_CHECKING:
    from uuid import UUID

    from app.infrastructure.db.models import Job, JobMatch


class LLMProvider(Protocol):
    """A large-language-model completion provider.

    Matches the interface documented in `docs/architecture/ai-architecture.md`
    exactly: `response_format` is a hint the provider uses to instruct the
    model to return structured output (e.g. "respond with only JSON
    matching this schema") — the provider still returns a plain `str`.
    Parsing and validating that string into a trustworthy structured
    object is the *caller's* responsibility (`JobScoringService`), not the
    provider's — so provider adapters stay simple, and validation logic
    isn't duplicated per provider.
    """

    async def complete(
        self, *, system: str, prompt: str, response_format: type[BaseModel] | None = None
    ) -> str: ...


class JobMatchRepository(Protocol):
    """Persistence operations `JobScoringService` and the matches API need."""

    async def create(self, *, profile_id: UUID, job: Job, result: MatchResult) -> JobMatch:
        """Persist a new scoring result as a `JobMatch` row.

        Every call creates a new row — a match is a point-in-time
        snapshot (see `docs/architecture/database-design.md` §3), so
        re-scoring the same profile/job pair is expected and produces
        score history over time, not an update to a prior row.
        """
        ...

    async def list_for_profile(
        self, *, profile_id: UUID, cursor: str | None, limit: int
    ) -> tuple[list[JobMatch], str | None]:
        """Return a page of matches for `profile_id`, newest first."""
        ...
