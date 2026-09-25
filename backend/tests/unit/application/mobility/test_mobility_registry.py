import pytest

from app.application.mobility.registry import MobilityProviderRegistry
from app.domain.entities.mobility.enums import BookingCapability, TransportMode
from app.domain.entities.mobility.models import (
    MobilityEvidence,
    MobilityOption,
    MobilityRequirement,
    ProviderCapability,
)
from app.domain.ports.mobility.ports import MobilityProviderPort


class DummyProvider(MobilityProviderPort):
    def __init__(self, provider_id: str, is_enabled: bool = True) -> None:
        self._provider_id = provider_id
        self._is_enabled = is_enabled

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=self._provider_id,
            name=f"Dummy {self._provider_id}",
            supported_modes=[TransportMode.BUS],
            has_route_data=True,
            has_timetable=True,
            has_realtime=False,
            has_service_alerts=False,
            has_fare_estimates=False,
            booking_capability=BookingCapability.NO_BOOKING,
            api_available=False,
            auth_required=False,
            is_enabled=self._is_enabled,
        )

    async def get_options(self, requirement: MobilityRequirement) -> list[MobilityOption]:
        return []

    async def get_live_status(self, option_id: str) -> MobilityEvidence | None:
        return None


def test_registry_registration_and_lookup():
    registry = MobilityProviderRegistry()
    provider = DummyProvider("test_p1")
    registry.register(provider)

    assert registry.get("test_p1") is provider
    assert registry.get("unknown") is None
    assert registry.is_enabled("test_p1") is True


def test_registry_enable_disable():
    registry = MobilityProviderRegistry()
    provider = DummyProvider("test_p1")
    registry.register(provider)

    registry.set_enabled("test_p1", False)
    assert registry.is_enabled("test_p1") is False
    assert len(registry.get_enabled_providers()) == 0

    caps = registry.list_capabilities()
    assert len(caps) == 1
    assert caps[0].is_enabled is False

    registry.set_enabled("test_p1", True)
    assert registry.is_enabled("test_p1") is True
    assert len(registry.get_enabled_providers()) == 1


def test_registry_unknown_provider_raises():
    registry = MobilityProviderRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.set_enabled("nonexistent", False)
