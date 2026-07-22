"""NormalizedJobPosting value object.

The common shape every job-source adapter (Adzuna, and later Greenhouse/
Lever) normalizes its provider-specific response into, before it ever
reaches the application layer. This is what keeps
`JobIngestionService` — and everything above it — completely unaware of
which external API a posting came from.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NormalizedJobPosting:
    """A job posting, normalized to a source-agnostic shape.

    Immutable (`frozen=True`) — a posting fetched from a source is a fact
    about a point-in-time API response; nothing downstream should mutate it
    in place.
    """

    source: str
    external_id: str
    title: str
    company: str
    location: str | None = None
    description: str | None = None
    url: str | None = None
