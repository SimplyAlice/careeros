from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Sequence

from app.application.mobility.dtos import (
    MobilityOptionDTO,
    MobilityOptionsResponseDTO,
    MobilityRequirementDTO,
    ProviderCapabilityDTO,
)
from app.application.mobility.registry import MobilityProviderRegistry
from app.domain.entities.mobility.enums import TransportMode
from app.domain.entities.mobility.models import MobilityOption, MobilityRequirement

logger = logging.getLogger(__name__)


class MobilityService:
    """Orchestrates transport candidate discovery across registered providers."""

    def __init__(self, registry: MobilityProviderRegistry) -> None:
        self.registry = registry

    async def get_options(self, req_dto: MobilityRequirementDTO) -> MobilityOptionsResponseDTO:
        requirement = req_dto.to_domain()
        domain_options = await self.find_options_for_requirement(requirement)
        option_dtos = [MobilityOptionDTO.from_domain(opt) for opt in domain_options]

        summary = f"Found {len(option_dtos)} transport option(s) from {requirement.origin} to {requirement.destination}."
        return MobilityOptionsResponseDTO(
            options=option_dtos,
            retrieved_at=datetime.now(UTC),
            total_options=len(option_dtos),
            query_summary=summary,
        )

    async def find_options_for_requirement(
        self, requirement: MobilityRequirement
    ) -> list[MobilityOption]:
        """Core domain query method: collects, filters, and sorts options safely."""
        enabled_providers = self.registry.get_enabled_providers()
        if not enabled_providers:
            logger.warning("No mobility providers currently registered and enabled.")
            return []

        # Filter providers matching requested modes
        eligible_providers = []
        for provider in enabled_providers:
            cap = provider.capability
            # Exclude if all supported modes are in excluded_modes
            if requirement.excluded_modes:
                if all(mode in requirement.excluded_modes for mode in cap.supported_modes):
                    continue
            # If preferred modes specified, we still check, but prioritize matching
            eligible_providers.append(provider)

        # Run providers concurrently with complete error isolation
        tasks = [provider.get_options(requirement) for provider in eligible_providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_options: list[MobilityOption] = []
        for provider, res in zip(eligible_providers, results, strict=False):
            if isinstance(res, Exception):
                logger.error(
                    "Mobility provider '%s' failed query: %s",
                    provider.capability.provider_id,
                    res,
                    exc_info=True,
                )
                continue
            if isinstance(res, list):
                all_options.extend(res)

        # Apply post-filtering (e.g. excluded modes at option level)
        filtered_options: list[MobilityOption] = []
        for opt in all_options:
            if requirement.excluded_modes and opt.mode in requirement.excluded_modes:
                continue
            if (
                requirement.max_walking_minutes is not None
                and opt.mode == TransportMode.WALK
                and opt.duration_minutes is not None
                and opt.duration_minutes > requirement.max_walking_minutes
            ):
                continue
            filtered_options.append(opt)

        # Sort options:
        # 1. Preferred modes first
        # 2. Options with known duration
        # 3. Walking if under 15 min, then public transit, then ride hail
        def sort_key(opt: MobilityOption) -> tuple[int, int, int]:
            is_preferred = 0 if (requirement.preferred_modes and opt.mode in requirement.preferred_modes) else 1
            duration = opt.duration_minutes if opt.duration_minutes is not None else 9999
            mode_order = {
                TransportMode.WALK: 0 if (opt.duration_minutes and opt.duration_minutes <= 15) else 3,
                TransportMode.BUS: 1,
                TransportMode.TRAIN: 1,
                TransportMode.RIDE_HAIL: 2,
                TransportMode.SHUTTLE: 2,
                TransportMode.CYCLE: 3,
                TransportMode.OTHER: 4,
            }.get(opt.mode, 5)
            return (is_preferred, mode_order, duration)

        filtered_options.sort(key=sort_key)
        return filtered_options

    def get_capabilities(self) -> list[ProviderCapabilityDTO]:
        """Return capabilities for all registered providers."""
        return [ProviderCapabilityDTO.from_domain(cap) for cap in self.registry.list_capabilities()]
