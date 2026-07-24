"""Application-level errors for profile use cases.

Distinct from `app.domain.entities.profile.ProfileValidationError`:
these describe use-case *state* problems (no profile exists yet; one
already exists) rather than data being invalid — a different failure
mode that the API layer maps to different HTTP status codes (404/409
here, vs 422/400 for validation errors).
"""

from __future__ import annotations


class ProfileNotFoundError(Exception):
    """Raised when an operation requires an existing profile and none exists."""


class ProfileAlreadyExistsError(Exception):
    """Raised on an attempt to create a profile when one already exists.

    CareerOS supports exactly one local profile at this milestone (see
    `docs/adr/0012-profile-management.md`) — this is the enforcement of
    that rule at the use-case boundary; `SqlAlchemyProfileRepository`
    additionally enforces it at the database level via a singleton unique
    index, so the guarantee holds even under a race.
    """
