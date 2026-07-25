"""MatchResult value object.

The structured, provider-agnostic shape a job-scoring call produces,
before it's persisted as a `JobMatch` row. Keeps the parsed/validated AI
response distinct from the ORM model, the same separation established for
`NormalizedJobPosting` (Milestone 3) between "what a provider gave us" and
"what we store."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MatchResult:
    """The outcome of scoring one profile against one job.

    Immutable — a scoring call is a fact about a point-in-time AI
    response; nothing downstream mutates it in place. `score` is
    constrained to 0-100 at construction, mirroring the database-level
    `ck_job_matches_score_range` constraint from Milestone 2 — the same
    two-layers-of-validation pattern used throughout this codebase.
    """

    score: Decimal
    rationale: str
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (0 <= self.score <= 100):
            msg = f"score must be between 0 and 100, got {self.score}."
            raise ValueError(msg)
        if not self.rationale.strip():
            msg = "rationale is required."
            raise ValueError(msg)
