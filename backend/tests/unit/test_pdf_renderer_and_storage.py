"""Unit tests for `FpdfPdfRenderer` and `LocalFileStorage`.

These exercise the real implementations (real fpdf2 rendering, real
filesystem writes to a temp directory) — not fakes — since they're thin
enough infrastructure adapters that a fake would test nothing meaningful.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from app.domain.entities.profile import Education, Experience, Profile, Skill
from app.domain.value_objects.generated_document import CoverLetterContent, TailoredResumeContent
from app.infrastructure.rendering.pdf_renderer import FpdfPdfRenderer
from app.infrastructure.storage.local_storage import LocalFileStorage


class FakeJob:
    def __init__(self) -> None:
        self.id = uuid4()
        self.title = "Cloud Engineer"
        self.company = "Acme Corp"


def _profile() -> Profile:
    return Profile(
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="+27 21 555 0100",
        location="Cape Town",
        skills=[Skill(name="Python"), Skill(name="Azure")],
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date=date(2020, 1, 1),
                currently_working=True,
                description="Built cloud infrastructure.",
            )
        ],
        education=[Education(institution="MIT", qualification="BSc", start_year=2016, end_year=2020)],
    )


class TestFpdfPdfRenderer:
    def test_render_resume_produces_nonempty_pdf_bytes(self) -> None:
        renderer = FpdfPdfRenderer()
        content = TailoredResumeContent(professional_summary="Strong engineer.", emphasized_skills=["Python"])

        pdf_bytes = renderer.render_resume(profile=_profile(), content=content)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 100

    def test_render_resume_handles_profile_with_no_experience_or_education(self) -> None:
        renderer = FpdfPdfRenderer()
        bare_profile = Profile(full_name="Ada Lovelace", email="ada@example.com")
        content = TailoredResumeContent(professional_summary="A summary.")

        pdf_bytes = renderer.render_resume(profile=bare_profile, content=content)

        assert pdf_bytes.startswith(b"%PDF")

    def test_render_cover_letter_produces_nonempty_pdf_bytes(self) -> None:
        renderer = FpdfPdfRenderer()
        content = CoverLetterContent(body="I would love to bring my skills to this role.")

        pdf_bytes = renderer.render_cover_letter(profile=_profile(), job=FakeJob(), content=content)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 100


class TestLocalFileStorage:
    def test_save_then_read_round_trips(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(str(tmp_path))

        path = storage.save(filename="resume.pdf", content=b"fake pdf bytes")
        read_back = storage.read(path=path)

        assert read_back == b"fake pdf bytes"

    def test_save_creates_the_base_directory_if_missing(self, tmp_path: Path) -> None:
        target_dir = tmp_path / "nested" / "documents"
        assert not target_dir.exists()

        storage = LocalFileStorage(str(target_dir))
        storage.save(filename="resume.pdf", content=b"bytes")

        assert target_dir.exists()

    def test_save_sanitizes_unsafe_filename_characters(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(str(tmp_path))

        path = storage.save(filename="../../etc/passwd", content=b"bytes")

        assert ".." not in Path(path).name
        assert "/" not in Path(path).name

    def test_save_twice_with_the_same_filename_produces_distinct_paths(self, tmp_path: Path) -> None:
        storage = LocalFileStorage(str(tmp_path))

        first_path = storage.save(filename="resume.pdf", content=b"version one")
        second_path = storage.save(filename="resume.pdf", content=b"version two")

        assert first_path != second_path
        assert storage.read(path=first_path) == b"version one"
        assert storage.read(path=second_path) == b"version two"
