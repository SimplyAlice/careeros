from __future__ import annotations

import logging
from typing import Iterable

from app.domain.entities.mobility.models import ProviderCapability
from app.domain.ports.mobility.ports import MobilityProviderPort

logger = logging.getLogger(__name__)


class MobilityProviderRegistry:
    """Central registry of verified transport provider adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, MobilityProviderPort] = {}
        self._disabled_providers: set[str] = set()

    def register(self, provider: MobilityProviderPort) -> None:
        """Register a provider adapter."""
        cap = provider.capability
        self._providers[cap.provider_id] = provider
        if not cap.is_enabled:
            self._disabled_providers.add(cap.provider_id)
        else:
            self._disabled_providers.discard(cap.provider_id)
        logger.info("Registered mobility provider: %s (%s)", cap.name, cap.provider_id)

    def get(self, provider_id: str) -> MobilityProviderPort | None:
        """Retrieve a registered provider by its unique identifier."""
        return self._providers.get(provider_id)

    def is_enabled(self, provider_id: str) -> bool:
        """Check if provider is registered and enabled."""
        return provider_id in self._providers and provider_id not in self._disabled_providers

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        """Enable or disable a provider at runtime."""
        if provider_id not in self._providers:
            raise KeyError(f"Provider '{provider_id}' is not registered.")
        if enabled:
            self._disabled_providers.discard(provider_id)
        else:
            self._disabled_providers.add(provider_id)

    def get_enabled_providers(self) -> list[MobilityProviderPort]:
        """Return all currently active and enabled provider adapters."""
        return [
            provider
            for provider_id, provider in self._providers.items()
            if provider_id not in self._disabled_providers
        ]

    def list_capabilities(self) -> list[ProviderCapability]:
        """Return declared capabilities for all registered providers."""
        caps = []
        for provider_id, provider in self._providers.items():
            cap = provider.capability
            # Reflect current enabled status in the registry
            if provider_id in self._disabled_providers and cap.is_enabled:
                cap = ProviderCapability(
                    provider_id=cap.provider_id,
                    name=cap.name,
                    supported_modes=cap.supported_modes,
                    has_route_data=cap.has_route_data,
                    has_timetable=cap.has_timetable,
                    has_realtime=cap.has_realtime,
                    has_service_alerts=cap.has_service_alerts,
                    has_fare_estimates=cap.has_fare_estimates,
                    booking_capability=cap.booking_capability,
                    api_available=cap.api_available,
                    auth_required=cap.auth_required,
                    official_source_url=cap.official_source_url,
                    is_enabled=False,
                    notes=cap.notes,
                )
            caps.append(cap)
        return caps

    def clear(self) -> None:
        """Clear all registered providers (primarily for test isolation)."""
        self._providers.clear()
        self._disabled_providers.clear()
