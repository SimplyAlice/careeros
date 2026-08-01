"""Unit tests for `validate_password_strength`."""

from __future__ import annotations

import pytest

from app.domain.value_objects.password_policy import WeakPasswordError, validate_password_strength


class TestPasswordPolicy:
    def test_valid_password_passes(self) -> None:
        validate_password_strength("Sup3rSecret")  # should not raise

    def test_too_short_password_is_rejected(self) -> None:
        with pytest.raises(WeakPasswordError, match="at least 8 characters"):
            validate_password_strength("Ab1")

    def test_password_without_a_letter_is_rejected(self) -> None:
        with pytest.raises(WeakPasswordError, match="at least one letter"):
            validate_password_strength("12345678")

    def test_password_without_a_digit_is_rejected(self) -> None:
        with pytest.raises(WeakPasswordError, match="at least one digit"):
            validate_password_strength("abcdefgh")

    def test_exactly_minimum_length_with_letter_and_digit_passes(self) -> None:
        validate_password_strength("abcdefg1")  # exactly 8 chars
