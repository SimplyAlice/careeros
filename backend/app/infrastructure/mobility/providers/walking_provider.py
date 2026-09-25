from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

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
from app.infrastructure.mobility.geo import estimate_network_distance_km


class WalkingProvider(MobilityProviderPort):
    """Provider-independent pedestrian mobility calculation."""

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="walking",
            name="Walking",
            supported_modes=[TransportMode.WALK],
            has_route_data=True,
            has_timetable=False,
            has_realtime=False,
            has_service_alerts=False,
            has_fare_estimates=True,
            booking_capability=BookingCapability.NO_BOOKING,
            api_available=True,
            auth_required=False,
            official_source_url=None,
            is_enabled=True,
            notes="Pedestrian navigation model. Monetary cost is 0 (free).",
        )

    async def get_options(self, requirement: MobilityRequirement) -> list[MobilityOption]:
        distance_km = estimate_network_distance_km(
            requirement.origin,
            requirement.destination,
            requirement.origin_coordinates,
            requirement.destination_coordinates,
        )

        # Skip walking if distance exceeds 10km unless walking was explicitly requested
        is_explicitly_requested = TransportMode.WALK in requirement.preferred_modes
        if distance_km > 10.0 and not is_explicitly_requested:
            return []

        # Average pedestrian pace: 4.8 km/h = 12.5 minutes per km
        duration_minutes = max(3, int(round(distance_km * 12.5)))

        dep_time = requirement.departure_time or datetime.now(UTC)
        arr_time = requirement.arrival_time
        if arr_time is not None and requirement.departure_time is None:
            dep_time = arr_time - timedelta(minutes=duration_minutes)
        else:
            arr_time = dep_time + timedelta(minutes=duration_minutes)

        evidence = MobilityEvidence(
            claim=f"Pedestrian journey of ~{distance_km:.1f} km at 4.8 km/h average walking pace.",
            source="Pedestrian Network Distance Calculator",
            source_type=MobilitySourceType.CALCULATED,
            observed_at=datetime.now(UTC),
            confidence=0.85,
            relevant_provider="walking",
        )

        option = MobilityOption(
            id=f"walk-{uuid4().hex[:8]}",
            provider_id="walking",
            provider_name="Walking",
            mode=TransportMode.WALK,
            origin=requirement.origin,
            destination=requirement.destination,
            departure_time=dep_time,
            arrival_time=arr_time,
            duration_minutes=duration_minutes,
            cost=Decimal("0"),  # Free! Zero cost is factual for walking
            cost_is_unknown=False,
            currency="ZAR",
            walking_duration_minutes=duration_minutes,
            transfers=0,
            availability="available",
            live_status=MobilityLiveStatus.SCHEDULED,
            booking_capability=BookingCapability.NO_BOOKING,
            booking_url=None,
            source="Pedestrian Network Model",
            source_type=MobilitySourceType.CALCULATED,
            retrieved_at=datetime.now(UTC),
            confidence=0.85,
            evidence=[evidence],
            summary=f"Walk {distance_km:.1f} km (~{duration_minutes} min)",
        )
        return [option]

    async def get_live_status(self, option_id: str) -> MobilityEvidence | None:
        return None
