"""Generated-document value objects.

The structured, provider-agnostic shape resume/cover-letter generation
produces, before it's rendered to PDF and persisted. Mirrors the
separation already established for `MatchResult` (Milestone 5): the
parsed/validated AI response is distinct from both the ORM model and the
rendered PDF bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TailoredResumeContent:
    """The AI-generated portion of a tailored resume.

    Deliberately narrow: only a professional summary and a re-ordered/
    emphasized skills list are AI-generated. Real experience and
    education entries are pulled directly from the candidate's actual
    `Profile` when the document is rendered — the AI never invents or
    rewrites employment history, dates, or titles (see
    `docs/adr/0014-resume-cover-letter-generation.md` for why this
    boundary exists and is enforced architecturally, not just by prompt
    instruction).
    """

    professional_summary: str
    emphasized_skills: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.professional_summary.strip():
            msg = "professional_summary is required."
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CoverLetterContent:
    """The AI-generated body of a cover letter.

    Greeting and closing are templated deterministically at render time
    (`infrastructure/rendering/pdf_renderer.py`), not AI-generated — this
    keeps the AI's job narrow (the substantive, job-specific paragraphs)
    and the surrounding structure predictable and typo-free.
    """

    body: str

    def __post_init__(self) -> None:
        if not self.body.strip():
            msg = "body is required."
            raise ValueError(msg)
