"""Unit tests for the generated-document domain value objects."""

from __future__ import annotations

import pytest

from app.domain.value_objects.generated_document import CoverLetterContent, TailoredResumeContent


class TestTailoredResumeContent:
    def test_valid_content_constructs_successfully(self) -> None:
        content = TailoredResumeContent(
            professional_summary="Strong backend engineer.", emphasized_skills=["Python"]
        )
        assert content.professional_summary == "Strong backend engineer."
        assert content.emphasized_skills == ["Python"]

    def test_blank_summary_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="professional_summary is required"):
            TailoredResumeContent(professional_summary="   ")

    def test_empty_emphasized_skills_defaults_to_empty_list(self) -> None:
        content = TailoredResumeContent(professional_summary="A summary.")
        assert content.emphasized_skills == []


class TestCoverLetterContent:
    def test_valid_content_constructs_successfully(self) -> None:
        content = CoverLetterContent(body="I am excited to apply for this role.")
        assert content.body == "I am excited to apply for this role."

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="body is required"):
            CoverLetterContent(body="   ")
