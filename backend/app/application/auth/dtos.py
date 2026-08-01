"""DTOs for authentication use cases.

Plain dataclasses, not Pydantic models — matching the convention already
established in `application/profile/dtos.py` and
`application/jobs/ports.py`: the application layer's input/output shapes
don't depend on the API layer's validation library.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterUserData:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class TokenPair:
    """An access/refresh token pair returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
