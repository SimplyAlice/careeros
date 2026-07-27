"""Ports for resume/cover-letter generation.

Reuses `LLMProvider` from `app/application/scoring/ports.py` (Milestone
5) rather than defining a second, duplicate LLM interface — the same
Anthropic adapter serves both use cases. `FileStorage` and `PdfRenderer`
are new ports specific to this milestone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from app.domain.entities.profile import Profile
    from app.domain.value_objects.generated_document import CoverLetterContent, TailoredResumeContent
    from app.infrastructure.db.models import GeneratedCoverLetter, GeneratedResume, Job


class PdfRenderer(Protocol):
    """Renders generated document content into PDF bytes.

    A `Protocol`, not a concrete class, so the rendering library
    (`fpdf2` today) is swappable the same way job sources and AI
    providers are — nothing above the infrastructure layer knows which
    PDF library is in use.
    """

    def render_resume(self, *, profile: Profile, content: TailoredResumeContent) -> bytes:
        """Render a full resume PDF: the AI-generated summary/skills
        emphasis, plus the profile's real (unmodified) experience and
        education entries.
        """
        ...

    def render_cover_letter(self, *, profile: Profile, job: Job, content: CoverLetterContent) -> bytes:
        """Render a full cover letter PDF for a specific job."""
        ...


class FileStorage(Protocol):
    """Persists rendered document bytes and returns a retrievable path/key.

    Implemented today by `LocalFileStorage` (local disk) — the interface
    is intentionally identical to what an Azure Blob Storage adapter
    would need (`docs/architecture/cloud-architecture.md` already
    documents Blob Storage as the eventual home for generated documents),
    so swapping storage backends later doesn't touch any calling code.
    """

    def save(self, *, filename: str, content: bytes) -> str:
        """Persist `content` under a name derived from `filename` and
        return the path/key it can be retrieved with.
        """
        ...

    def read(self, *, path: str) -> bytes:
        """Retrieve previously-saved content by the path/key `save` returned."""
        ...


class GeneratedResumeRepository(Protocol):
    """Persistence operations for generated resumes."""

    async def create(
        self, *, profile_id: UUID, job_id: UUID | None, content: TailoredResumeContent, file_path: str
    ) -> GeneratedResume:
        """Persist a new generated resume. Every call creates a new row —
        a generated resume is a versioned snapshot, not a mutable record
        (the same point-in-time-snapshot pattern used for `JobMatch`,
        Milestone 5).
        """
        ...

    async def get_by_id(self, *, profile_id: UUID, resume_id: UUID) -> GeneratedResume | None:
        """Look up a specific generated resume, scoped to the owning profile."""
        ...

    async def list_for_profile(
        self, *, profile_id: UUID, cursor: str | None, limit: int
    ) -> tuple[list[GeneratedResume], str | None]:
        """Return a page of generated resumes for `profile_id`, newest first."""
        ...


class GeneratedCoverLetterRepository(Protocol):
    """Persistence operations for generated cover letters."""

    async def create(
        self, *, profile_id: UUID, job: Job, content: CoverLetterContent, file_path: str
    ) -> GeneratedCoverLetter:
        """Persist a new generated cover letter."""
        ...

    async def get_by_id(self, *, profile_id: UUID, cover_letter_id: UUID) -> GeneratedCoverLetter | None:
        """Look up a specific generated cover letter, scoped to the owning profile."""
        ...

    async def list_for_profile(
        self, *, profile_id: UUID, cursor: str | None, limit: int
    ) -> tuple[list[GeneratedCoverLetter], str | None]:
        """Return a page of generated cover letters for `profile_id`, newest first."""
        ...
