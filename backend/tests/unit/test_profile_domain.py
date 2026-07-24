"""Unit tests for the `Profile` domain entity and its children.

Pure domain logic — no database, no HTTP, no fakes needed. These are the
tests that actually prove the business rules Milestone 4 asks for
("validate email, phone length, required fields, max string lengths,
non-negative years of experience, reasonable salary expectation, prevent
duplicate skills") are enforced, independent of whatever persists or
serves them.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.profile import (
    DuplicateSkillError,
    Education,
    Experience,
    Profile,
    ProfileValidationError,
    RemotePreference,
    ResumeMetadata,
    Skill,
)


def _valid_profile(**overrides: object) -> Profile:
    defaults: dict[str, object] = {"full_name": "Ada Lovelace", "email": "ada@example.com"}
    defaults.update(overrides)
    return Profile(**defaults)  # type: ignore[arg-type]


class TestProfileRequiredFields:
    def test_valid_profile_constructs_successfully(self) -> None:
        profile = _valid_profile()
        assert profile.full_name == "Ada Lovelace"
        assert profile.email == "ada@example.com"
        assert profile.remote_preference is RemotePreference.FLEXIBLE

    def test_blank_full_name_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="Full name is required"):
            _valid_profile(full_name="   ")

    def test_full_name_over_max_length_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="at most 255 characters"):
            _valid_profile(full_name="A" * 256)

    def test_full_name_is_stripped(self) -> None:
        profile = _valid_profile(full_name="  Ada Lovelace  ")
        assert profile.full_name == "Ada Lovelace"


class TestEmailValidation:
    @pytest.mark.parametrize(
        "bad_email", ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign.com"]
    )
    def test_invalid_email_formats_are_rejected(self, bad_email: str) -> None:
        with pytest.raises(ProfileValidationError, match="not a valid email"):
            _valid_profile(email=bad_email)

    def test_valid_email_is_accepted(self) -> None:
        profile = _valid_profile(email="ada.lovelace+careers@example.co.uk")
        assert profile.email == "ada.lovelace+careers@example.co.uk"


class TestPhoneValidation:
    def test_none_phone_is_allowed(self) -> None:
        profile = _valid_profile(phone=None)
        assert profile.phone is None

    def test_too_short_phone_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="7-32 characters"):
            _valid_profile(phone="123")

    def test_too_long_phone_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="7-32 characters"):
            _valid_profile(phone="1" * 33)

    def test_phone_with_invalid_characters_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="7-32 characters"):
            _valid_profile(phone="call-me-maybe")

    def test_well_formed_phone_is_accepted(self) -> None:
        profile = _valid_profile(phone="+27 21 555 0100")
        assert profile.phone == "+27 21 555 0100"


class TestYearsExperienceValidation:
    def test_negative_years_experience_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="years_experience must be between"):
            _valid_profile(years_experience=-1)

    def test_unreasonably_high_years_experience_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="years_experience must be between"):
            _valid_profile(years_experience=71)

    def test_zero_years_experience_is_allowed(self) -> None:
        profile = _valid_profile(years_experience=0)
        assert profile.years_experience == 0


class TestSalaryExpectationValidation:
    def test_negative_salary_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="cannot be negative"):
            _valid_profile(salary_expectation=Decimal(-1))

    def test_unreasonably_high_salary_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="must be at most"):
            _valid_profile(salary_expectation=Decimal("999_999_999"))

    def test_reasonable_salary_is_accepted(self) -> None:
        profile = _valid_profile(salary_expectation=Decimal("850000.00"))
        assert profile.salary_expectation == Decimal("850000.00")


class TestDuplicateSkillPrevention:
    def test_duplicate_skill_names_are_rejected_at_construction(self) -> None:
        with pytest.raises(DuplicateSkillError):
            _valid_profile(skills=[Skill(name="Python"), Skill(name="python")])

    def test_distinct_skills_are_accepted(self) -> None:
        profile = _valid_profile(skills=[Skill(name="Python"), Skill(name="Azure")])
        assert [s.name for s in profile.skills] == ["Python", "Azure"]

    def test_replace_skills_rejects_duplicates(self) -> None:
        profile = _valid_profile()
        with pytest.raises(DuplicateSkillError):
            profile.replace_skills([Skill(name="SQL"), Skill(name="  sql  ")])

    def test_replace_skills_accepts_distinct_list(self) -> None:
        profile = _valid_profile(skills=[Skill(name="Python")])
        profile.replace_skills([Skill(name="Go"), Skill(name="Rust")])
        assert [s.name for s in profile.skills] == ["Go", "Rust"]


class TestExperienceValidation:
    def test_currently_working_with_end_date_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="cannot have an end_date"):
            Experience(
                company="Acme",
                title="Engineer",
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1),
                currently_working=True,
            )

    def test_end_date_before_start_date_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="cannot be before start_date"):
            Experience(
                company="Acme", title="Engineer", start_date=date(2022, 1, 1), end_date=date(2021, 1, 1)
            )

    def test_valid_experience_is_accepted(self) -> None:
        experience = Experience(
            company="Acme", title="Engineer", start_date=date(2020, 1, 1), currently_working=True
        )
        assert experience.company == "Acme"


class TestEducationValidation:
    def test_end_year_before_start_year_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="end_year cannot be before start_year"):
            Education(institution="MIT", qualification="BSc", start_year=2020, end_year=2019)

    def test_unreasonable_start_year_is_rejected(self) -> None:
        with pytest.raises(ProfileValidationError, match="start_year must be between"):
            Education(institution="MIT", qualification="BSc", start_year=1800)

    def test_valid_education_is_accepted(self) -> None:
        education = Education(institution="MIT", qualification="BSc", start_year=2018, end_year=2022)
        assert education.end_year == 2022


class TestResumeMetadataValidation:
    def test_blank_filename_is_rejected(self) -> None:
        from datetime import UTC, datetime

        with pytest.raises(ProfileValidationError, match="Resume filename is required"):
            ResumeMetadata(filename="  ", uploaded_at=datetime.now(UTC))


class TestApplyPatch:
    def test_apply_patch_updates_only_given_fields(self) -> None:
        profile = _valid_profile(headline="Old headline")
        profile.apply_patch({"headline": "New headline"})
        assert profile.headline == "New headline"
        assert profile.full_name == "Ada Lovelace"

    def test_apply_patch_can_clear_a_nullable_field(self) -> None:
        profile = _valid_profile(headline="Old headline")
        profile.apply_patch({"headline": None})
        assert profile.headline is None

    def test_apply_patch_re_validates(self) -> None:
        profile = _valid_profile()
        with pytest.raises(ProfileValidationError, match="not a valid email"):
            profile.apply_patch({"email": "not-an-email"})

    def test_apply_patch_rejects_unknown_field(self) -> None:
        profile = _valid_profile()
        with pytest.raises(ProfileValidationError, match="unknown field"):
            profile.apply_patch({"nonexistent_field": "value"})
