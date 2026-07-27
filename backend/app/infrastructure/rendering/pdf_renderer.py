"""PDF rendering via fpdf2.

Implements `PdfRenderer` (`app/application/documents/ports.py`). fpdf2 was
chosen over WeasyPrint/ReportLab specifically because it's pure Python
with no system-level dependencies (no Cairo/Pango to install in the
Docker image) — see `docs/adr/0014-resume-cover-letter-generation.md`.

Layout is deliberately plain — single column, standard headings, no
tables or graphics in the body — matching the ATS-safe resume guidance in
`docs/architecture/system-design.md` (FR-10).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from fpdf import FPDF

if TYPE_CHECKING:
    from app.domain.entities.profile import Profile
    from app.domain.value_objects.generated_document import CoverLetterContent, TailoredResumeContent
    from app.infrastructure.db.models import Job

_MARGIN_MM = 20
_BODY_FONT_SIZE = 11
_HEADING_FONT_SIZE = 13
_TITLE_FONT_SIZE = 16


def _new_document() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=_MARGIN_MM)
    pdf.set_margins(left=_MARGIN_MM, top=_MARGIN_MM, right=_MARGIN_MM)
    pdf.add_page()
    return pdf


def _heading(pdf: FPDF, text: str) -> None:
    pdf.ln(4)
    pdf.set_font("Helvetica", style="B", size=_HEADING_FONT_SIZE)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=_BODY_FONT_SIZE)


def _paragraph(pdf: FPDF, text: str) -> None:
    pdf.multi_cell(0, 6, text)
    pdf.ln(2)


def _format_date_range(start: date, end: date | None, currently_working: bool) -> str:
    start_text = start.strftime("%b %Y")
    if currently_working:
        return f"{start_text} - Present"
    if end is not None:
        return f"{start_text} - {end.strftime('%b %Y')}"
    return start_text


class FpdfPdfRenderer:
    """Renders `TailoredResumeContent`/`CoverLetterContent` to PDF bytes via fpdf2."""

    def render_resume(self, *, profile: Profile, content: TailoredResumeContent) -> bytes:
        pdf = _new_document()

        pdf.set_font("Helvetica", style="B", size=_TITLE_FONT_SIZE)
        pdf.cell(0, 10, profile.full_name, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", size=_BODY_FONT_SIZE)
        contact_parts = [part for part in (profile.email, profile.phone, profile.location) if part]
        if contact_parts:
            pdf.cell(0, 6, " | ".join(contact_parts), new_x="LMARGIN", new_y="NEXT")

        _heading(pdf, "Professional Summary")
        _paragraph(pdf, content.professional_summary)

        if content.emphasized_skills:
            _heading(pdf, "Skills")
            _paragraph(pdf, ", ".join(content.emphasized_skills))

        if profile.experience:
            _heading(pdf, "Experience")
            for experience_entry in profile.experience:
                date_range = _format_date_range(
                    experience_entry.start_date, experience_entry.end_date, experience_entry.currently_working
                )
                pdf.set_font("Helvetica", style="B", size=_BODY_FONT_SIZE)
                pdf.cell(
                    0,
                    6,
                    f"{experience_entry.title}, {experience_entry.company}",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                pdf.set_font("Helvetica", style="I", size=_BODY_FONT_SIZE)
                pdf.cell(0, 6, date_range, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", size=_BODY_FONT_SIZE)
                if experience_entry.description:
                    _paragraph(pdf, experience_entry.description)
                pdf.ln(2)

        if profile.education:
            _heading(pdf, "Education")
            for education_entry in profile.education:
                year_range = (
                    f"{education_entry.start_year}-{education_entry.end_year}"
                    if education_entry.end_year
                    else f"{education_entry.start_year}-"
                )
                pdf.set_font("Helvetica", style="B", size=_BODY_FONT_SIZE)
                pdf.cell(
                    0,
                    6,
                    f"{education_entry.qualification}, {education_entry.institution}",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                pdf.set_font("Helvetica", style="I", size=_BODY_FONT_SIZE)
                pdf.cell(0, 6, year_range, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", size=_BODY_FONT_SIZE)

        return bytes(pdf.output())

    def render_cover_letter(self, *, profile: Profile, job: Job, content: CoverLetterContent) -> bytes:
        pdf = _new_document()
        pdf.set_font("Helvetica", size=_BODY_FONT_SIZE)

        today = date.today()  # noqa: DTZ011 — a calendar date for a letterhead, not a precise instant
        pdf.cell(0, 6, today.isoformat(), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.cell(0, 6, f"Re: Application for {job.title} at {job.company}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        pdf.cell(0, 6, "Dear Hiring Team,", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        _paragraph(pdf, content.body)

        pdf.ln(4)
        pdf.cell(0, 6, "Sincerely,", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, profile.full_name, new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())
