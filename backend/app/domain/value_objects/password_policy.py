"""Password policy — the business rule for what counts as an acceptable password.

A small, standalone domain module rather than an addition to
`domain/entities/profile.py`: authentication is a distinct concern from
the candidate profile, and this milestone deliberately doesn't touch
Profile's domain module (see `docs/adr/0015-authentication.md`).
"""

from __future__ import annotations

import re

_MIN_LENGTH = 8
_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


class WeakPasswordError(ValueError):
    """Raised when a candidate password doesn't meet the minimum policy.

    A subclass of `ValueError` (not a bare custom exception), matching
    the convention `ProfileValidationError` already established: business
    rule violations are catchable as "this input was invalid" at the API
    boundary without special-casing every domain module's own exception
    type.
    """


def validate_password_strength(password: str) -> None:
    """Raise `WeakPasswordError` if `password` doesn't meet the minimum policy.

    Deliberately modest requirements (length 8+, at least one letter and
    one digit) — strict enough to rule out trivially guessable passwords
    without demanding a specific mix of symbols/casing that mostly
    frustrates users without meaningfully improving security.
    """
    if len(password) < _MIN_LENGTH:
        msg = f"Password must be at least {_MIN_LENGTH} characters."
        raise WeakPasswordError(msg)
    if not _HAS_LETTER.search(password):
        msg = "Password must contain at least one letter."
        raise WeakPasswordError(msg)
    if not _HAS_DIGIT.search(password):
        msg = "Password must contain at least one digit."
        raise WeakPasswordError(msg)
