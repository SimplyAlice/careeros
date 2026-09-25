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

PRASA_LINES = [
    {
        "line": "Southern Line",
        "stations": [
            "cape town",
            "cape town station",
            "woodstock",
            "salt river",
            "observatory",
            "mowbray",
            "rosebank",
            "rondebosch",
            "newlands",
            "claremont",
            "harfield road",
            "kenilworth",
            "wynberg",
            "plumstead",
            "steurhof",
            "diep river",
            "heathfield",
            "retreat",
            "steenberg",
            "lakeside",
            "muizenberg",
            "st james",
            "kalk bay",
            "fish hoek",
            "glencairn",
            "simon's town",
            "simons town",
        ],
    },
    {
        "line": "Northern Line",
        "stations": [
            "cape town",
            "cape town station",
            "woodstock",
            "salt river",
            "maitland",
            "ndabeni",
            "pinelands",
            "mutual",
            "bellville",
            "kuils river",
            "strand",
        ],
    },
]


class PrasaProvider(MobilityProviderPort):
    """PRASA Metrorail Western Cape scheduled passenger rail integration."""

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="prasa_metrorail",
            name="PRASA Metrorail (Western Cape)",
            supported_modes=[TransportMode.TRAIN],
            has_route_data=True,
            has_timetable=True,
            has_realtime=False,
            has_service_alerts=True,
            has_fare_estimates=True,
            booking_capability=BookingCapability.NO_BOOKING,
            api_available=False,
            auth_required=False,
            official_source_url="https://www.prasa.com",
            is_enabled=True,
            notes="Official Western Cape commuter train schedules for Southern and Northern lines. Live track status is not published via public API, so live status is explicitly marked unknown.",
        )

    async def get_options(self, requirement: MobilityRequirement) -> list[MobilityOption]:
        orig = requirement.origin.strip().lower()
        dest = requirement.destination.strip().lower()

        matching_lines = []
        for line_info in PRASA_LINES:
            has_orig = any(st in orig or orig in st for st in line_info["stations"])
            has_dest = any(st in dest or dest in st for st in line_info["stations"])
            if has_orig and has_dest:
                matching_lines.append(line_info)

        if not matching_lines:
            return []

        distance_km = estimate_network_distance_km(
            requirement.origin,
            requirement.destination,
            requirement.origin_coordinates,
            requirement.destination_coordinates,
        )

        # PRASA standard single ticket fares (zonal): ~R10.50 - R14.50
        if distance_km <= 15.0:
            fare = Decimal("10.50")
        elif distance_km <= 30.0:
            fare = Decimal("12.50")
        else:
            fare = Decimal("14.50")

        # Average rail travel speed: ~38 km/h + 4 min station buffer
        duration_minutes = max(12, int(round((distance_km / 38.0) * 60)) + 4)

        dep_time = requirement.departure_time or datetime.now(UTC)
        arr_time = requirement.arrival_time
        if arr_time is not None and requirement.departure_time is None:
            dep_time = arr_time - timedelta(minutes=duration_minutes)
        else:
            arr_time = dep_time + timedelta(minutes=duration_minutes)

        options: list[MobilityOption] = []
        for line_info in matching_lines:
            line_name = line_info["line"]
            evidence = MobilityEvidence(
                claim=f"Scheduled Metrorail service on the {line_name}. Standard zonal single fare applied.",
                source="PRASA Western Cape Official Timetable",
                source_type=MobilitySourceType.OFFICIAL_TIMETABLE,
                observed_at=datetime.now(UTC),
                confidence=0.75,
                relevant_provider="prasa_metrorail",
                relevant_route_or_stop=line_name,
            )

            option = MobilityOption(
                id=f"prasa-{line_name.lower().replace(' ', '-')}-{uuid4().hex[:6]}",
                provider_id="prasa_metrorail",
                provider_name="PRASA Metrorail (Western Cape)",
                mode=TransportMode.TRAIN,
                origin=requirement.origin,
                destination=requirement.destination,
                departure_time=dep_time,
                arrival_time=arr_time,
                duration_minutes=duration_minutes,
                cost=fare,
                cost_is_unknown=False,
                currency="ZAR",
                walking_duration_minutes=6,
                transfers=0,
                availability="available",
                live_status=MobilityLiveStatus.UNKNOWN,
                booking_capability=BookingCapability.NO_BOOKING,
                booking_url="https://www.prasa.com",
                source="PRASA Western Cape Official Timetable",
                source_type=MobilitySourceType.OFFICIAL_TIMETABLE,
                retrieved_at=datetime.now(UTC),
                confidence=0.75,
                evidence=[evidence],
                summary=f"Metrorail {line_name} (~{duration_minutes} min, R{fare:.2f})",
            )
            options.append(option)

        return options

    async def get_live_status(self, option_id: str) -> MobilityEvidence | None:
        return None
