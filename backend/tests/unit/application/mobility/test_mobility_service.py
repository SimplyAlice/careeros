from datetime import UTC, datetime
from decimal import Decimal
import pytest

from app.application.mobility.dtos import MobilityRequirementDTO
from app.application.mobility.registry import MobilityProviderRegistry
from app.application.mobility.service import MobilityService
from app.domain.entities.mobility.enums import (
    BookingCapability,
    MobilityLiveStatus,
    MobilitySourceType,
    TransportMode,
)
from app.domain.entities.mobility.models import (
    MobilityEvidence,
    MobilityOption,
    MobilityRequirement,
    ProviderCapability,
)
from app.domain.ports.mobility.ports import MobilityProviderPort


class MockSuccessProvider(MobilityProviderPort):
    def __init__(self, provider_id: str, mode: TransportMode, duration: int) -> None:
        self._provider_id = provider_id
        self._mode = mode
        self._duration = duration

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=self._provider_id,
            name=f"Mock {self._provider_id}",
            supported_modes=[self._mode],
            has_route_data=True,
            has_timetable=True,
            has_realtime=False,
            has_service_alerts=False,
            has_fare_estimates=True,
            booking_capability=BookingCapability.NO_BOOKING,
            api_available=False,
            auth_required=False,
            is_enabled=True,
        )

    async def get_options(self, requirement: MobilityRequirement) -> list[MobilityOption]:
        return [
            MobilityOption(
                id=f"{self._provider_id}-1",
                provider_id=self._provider_id,
                provider_name=f"Mock {self._provider_id}",
                mode=self._mode,
                origin=requirement.origin,
                destination=requirement.destination,
                duration_minutes=self._duration,
                cost=Decimal("15.00"),
                currency="ZAR",
            )
        ]

    async def get_live_status(self, option_id: str) -> MobilityEvidence | None:
        return None


class MockFailingProvider(MobilityProviderPort):
    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="failing_provider",
            name="Failing Provider",
            supported_modes=[TransportMode.BUS],
            has_route_data=True,
            has_timetable=True,
            has_realtime=False,
            has_service_alerts=False,
            has_fare_estimates=False,
            booking_capability=BookingCapability.NO_BOOKING,
            api_available=False,
            auth_required=False,
            is_enabled=True,
        )

    async def get_options(self, requirement: MobilityRequirement) -> list[MobilityOption]:
        raise RuntimeError("External network timeout or scrape error")

    async def get_live_status(self, option_id: str) -> MobilityEvidence | None:
        return None


@pytest.mark.asyncio
async def test_service_provider_failure_isolation():
    registry = MobilityProviderRegistry()
    registry.register(MockSuccessProvider("p_good", TransportMode.BUS, 25))
    registry.register(MockFailingProvider())

    service = MobilityService(registry)
    req = MobilityRequirementDTO(origin="Gardens", destination="Waterfront")

    # The failing provider must NOT crash the service query
    response = await service.get_options(req)
    assert len(response.options) == 1
    assert response.options[0].provider_id == "p_good"


@pytest.mark.asyncio
async def test_service_mode_filtering():
    registry = MobilityProviderRegistry()
    registry.register(MockSuccessProvider("p_bus", TransportMode.BUS, 20))
    registry.register(MockSuccessProvider("p_walk", TransportMode.WALK, 15))
    registry.register(MockSuccessProvider("p_uber", TransportMode.RIDE_HAIL, 10))

    service = MobilityService(registry)

    # Exclude ride-hail
    req_no_rides = MobilityRequirementDTO(
        origin="Gardens",
        destination="Waterfront",
        excluded_modes=[TransportMode.RIDE_HAIL],
    )
    res_no_rides = await service.get_options(req_no_rides)
    modes = [opt.mode for opt in res_no_rides.options]
    assert TransportMode.RIDE_HAIL not in modes
    assert TransportMode.BUS in modes
    assert TransportMode.WALK in modes

    # Prefer ride-hail: ride-hail should be prioritized first
    req_prefer_rides = MobilityRequirementDTO(
        origin="Gardens",
        destination="Waterfront",
        preferred_modes=[TransportMode.RIDE_HAIL],
    )
    res_prefer_rides = await service.get_options(req_prefer_rides)
    assert res_prefer_rides.options[0].mode == TransportMode.RIDE_HAIL


@pytest.mark.asyncio
async def test_service_max_walking_time_filter():
    registry = MobilityProviderRegistry()
    registry.register(MockSuccessProvider("p_walk", TransportMode.WALK, 45))
    registry.register(MockSuccessProvider("p_bus", TransportMode.BUS, 20))

    service = MobilityService(registry)
    req = MobilityRequirementDTO(
        origin="Gardens",
        destination="Camps Bay",
        max_walking_minutes=20,
    )
    res = await service.get_options(req)
    modes = [opt.mode for opt in res.options]
    assert TransportMode.WALK not in modes
    assert TransportMode.BUS in modes
