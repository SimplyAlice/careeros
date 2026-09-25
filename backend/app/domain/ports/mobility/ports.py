from __future__ import annotations

from typing import Protocol

from app.domain.entities.mobility.models import (
    MobilityEvidence,
    MobilityOption,
    MobilityRequirement,
    ProviderCapability,
)


class MobilityProviderPort(Protocol):
    """Port interface that all mobility transport providers must fulfill."""

    @property
    def capability(self) -> ProviderCapability:
        """Declares the verified capabilities and constraints of the provider."""
        ...

    async def get_options(self, requirement: MobilityRequirement) -> list[MobilityOption]:
        """Produce concrete travel options matching the requirement."""
        ...

    async def get_live_status(self, option_id: str) -> MobilityEvidence | None:
        """Inspect live status or disruption evidence for a specific journey/option."""
        ...
