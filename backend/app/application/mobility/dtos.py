from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

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


@dataclass
class MobilityRequirementDTO:
    origin: str
    destination: str
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    date: date | None = None
    party_size: int = 1
    preferred_modes: list[TransportMode] = field(default_factory=list)
    excluded_modes: list[TransportMode] = field(default_factory=list)
    max_walking_minutes: int | None = None
    origin_coordinates: tuple[float, float] | None = None
    destination_coordinates: tuple[float, float] | None = None

    def to_domain(self) -> MobilityRequirement:
        return MobilityRequirement(
            origin=self.origin,
            destination=self.destination,
            departure_time=self.departure_time,
            arrival_time=self.arrival_time,
            date=self.date,
            party_size=self.party_size,
            preferred_modes=self.preferred_modes,
            excluded_modes=self.excluded_modes,
            max_walking_minutes=self.max_walking_minutes,
            origin_coordinates=self.origin_coordinates,
            destination_coordinates=self.destination_coordinates,
        )


@dataclass
class MobilityEvidenceDTO:
    claim: str
    source: str
    source_type: MobilitySourceType
    observed_at: datetime
    retrieved_at: datetime
    expires_at: datetime | None
    confidence: float
    relevant_provider: str
    relevant_route_or_stop: str | None

    @classmethod
    def from_domain(cls, entity: MobilityEvidence) -> MobilityEvidenceDTO:
        return cls(
            claim=entity.claim,
            source=entity.source,
            source_type=entity.source_type,
            observed_at=entity.observed_at,
            retrieved_at=entity.retrieved_at,
            expires_at=entity.expires_at,
            confidence=entity.confidence,
            relevant_provider=entity.relevant_provider,
            relevant_route_or_stop=entity.relevant_route_or_stop,
        )


@dataclass
class MobilityOptionDTO:
    id: str
    provider_id: str
    provider_name: str
    mode: TransportMode
    origin: str
    destination: str
    departure_time: datetime | None
    arrival_time: datetime | None
    duration_minutes: int | None
    cost: Decimal | None
    cost_is_unknown: bool
    currency: str
    walking_duration_minutes: int | None
    transfers: int
    availability: str
    live_status: MobilityLiveStatus
    booking_capability: BookingCapability
    booking_url: str | None
    source: str
    source_type: MobilitySourceType
    retrieved_at: datetime
    confidence: float
    summary: str
    evidence: list[MobilityEvidenceDTO] = field(default_factory=list)

    @classmethod
    def from_domain(cls, entity: MobilityOption) -> MobilityOptionDTO:
        return cls(
            id=entity.id,
            provider_id=entity.provider_id,
            provider_name=entity.provider_name,
            mode=entity.mode,
            origin=entity.origin,
            destination=entity.destination,
            departure_time=entity.departure_time,
            arrival_time=entity.arrival_time,
            duration_minutes=entity.duration_minutes,
            cost=entity.cost,
            cost_is_unknown=entity.cost_is_unknown,
            currency=entity.currency,
            walking_duration_minutes=entity.walking_duration_minutes,
            transfers=entity.transfers,
            availability=entity.availability,
            live_status=entity.live_status,
            booking_capability=entity.booking_capability,
            booking_url=entity.booking_url,
            source=entity.source,
            source_type=entity.source_type,
            retrieved_at=entity.retrieved_at,
            confidence=entity.confidence,
            summary=entity.summary,
            evidence=[MobilityEvidenceDTO.from_domain(e) for e in entity.evidence],
        )


@dataclass
class ProviderCapabilityDTO:
    provider_id: str
    name: str
    supported_modes: list[TransportMode]
    has_route_data: bool
    has_timetable: bool
    has_realtime: bool
    has_service_alerts: bool
    has_fare_estimates: bool
    booking_capability: BookingCapability
    api_available: bool
    auth_required: bool
    official_source_url: str | None
    is_enabled: bool
    notes: str

    @classmethod
    def from_domain(cls, entity: ProviderCapability) -> ProviderCapabilityDTO:
        return cls(
            provider_id=entity.provider_id,
            name=entity.name,
            supported_modes=entity.supported_modes,
            has_route_data=entity.has_route_data,
            has_timetable=entity.has_timetable,
            has_realtime=entity.has_realtime,
            has_service_alerts=entity.has_service_alerts,
            has_fare_estimates=entity.has_fare_estimates,
            booking_capability=entity.booking_capability,
            api_available=entity.api_available,
            auth_required=entity.auth_required,
            official_source_url=entity.official_source_url,
            is_enabled=entity.is_enabled,
            notes=entity.notes,
        )


@dataclass
class MobilityOptionsResponseDTO:
    options: list[MobilityOptionDTO]
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_options: int = 0
    query_summary: str = ""
