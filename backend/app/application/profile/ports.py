"""Port for profile persistence.

`ProfileService` depends on this `Protocol`, not on SQLAlchemy —
`SqlAlchemyProfileRepository` (infrastructure layer) implements it
structurally, following the same pattern established for jobs in
Milestone 3 (`app/application/jobs/ports.py`).
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.profile import Profile


class ProfileRepository(Protocol):
    """Persistence operations `ProfileService` needs.

    Deliberately narrow: `get()`/`create()`/`update()` for the single
    profile this milestone supports — no `list()`, no `delete()`, no
    `profile_id` parameters, because there is exactly one profile and no
    use case yet needs to address it by ID. Widening this interface is
    straightforward once multi-profile support is real (see the ADR's
    "future migration path").
    """

    async def get(self) -> Profile | None:
        """Return the single profile, or `None` if it hasn't been created yet."""
        ...

    async def create(self, profile: Profile) -> Profile:
        """Persist a new profile.

        Implementations must reject this if a profile already exists —
        `SqlAlchemyProfileRepository` enforces this via a database-level
        singleton constraint, raising `ProfileAlreadyExistsError`.
        """
        ...

    async def update(self, profile: Profile) -> Profile:
        """Persist changes to the existing profile (identified by `profile.id`)."""
        ...
