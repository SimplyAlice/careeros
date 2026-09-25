from datetime import UTC, datetime, timedelta
from decimal import Decimal
import pytest

from app.domain.entities.mobility.enums import (
    BookingCapability,
    MobilityLiveStatus,
    MobilitySourceType,
    TransportMode,
    get_source_hierarchy_weight,
)
from app.domain.entities.mobility.models import (
    MobilityEvidence,
    MobilityOption,
    MobilityRequirement,
    ProviderCapability,
)


def test_mobility_requirement_valid():
    req = MobilityRequirement(
        origin="Kloof Street",
        destination="V&A Waterfront",
        party_size=2,
    )
    assert req.origin == "Kloof Street"
    assert req.destination == "V&A Waterfront"
    assert req.party_size == 2


def test_mobility_requirement_invalid_origin_dest():
    with pytest.raises(ValueError, match="origin cannot be empty"):
        MobilityRequirement(origin="", destination="Waterfront")

    with pytest.raises(ValueError, match="destination cannot be empty"):
        MobilityRequirement(origin="Gardens", destination="   ")

    with pytest.raises(ValueError, match="Party size must be at least 1"):
        MobilityRequirement(origin="Gardens", destination="Waterfront", party_size=0)


def test_mobility_requirement_invalid_time_order():
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="Arrival time cannot be before departure time"):
        MobilityRequirement(
            origin="Gardens",
            destination="Waterfront",
            departure_time=now + timedelta(hours=2),
            arrival_time=now + timedelta(hours=1),
        )


def test_mobility_option_unknown_vs_zero_cost():
    # Walking: zero cost is known and factual
    opt_walk = MobilityOption(
        id="walk-1",
        provider_id="walking",
        provider_name="Walking",
        mode=TransportMode.WALK,
        origin="Gardens",
        destination="Waterfront",
        cost=Decimal("0"),
        cost_is_unknown=False,
    )
    assert opt_walk.cost == Decimal("0")
    assert not opt_walk.cost_is_unknown

    # Uber: unknown cost is NOT zero
    opt_uber = MobilityOption(
        id="uber-1",
        provider_id="uber",
        provider_name="Uber",
        mode=TransportMode.RIDE_HAIL,
        origin="Gardens",
        destination="Waterfront",
        cost=None,
    )
    assert opt_uber.cost is None
    assert opt_uber.cost_is_unknown is True


def test_mobility_option_negative_cost_raises():
    with pytest.raises(ValueError, match="Cost cannot be negative"):
        MobilityOption(
            id="test-1",
            provider_id="test",
            provider_name="Test",
            mode=TransportMode.BUS,
            origin="A",
            destination="B",
            cost=Decimal("-10.00"),
        )


def test_mobility_evidence_validation():
    now = datetime.now(UTC)
    ev = MobilityEvidence(
        claim="Official scheduled bus arrival at 14:30",
        source="MyCiTi Timetable",
        source_type=MobilitySourceType.OFFICIAL_TIMETABLE,
        observed_at=now,
        confidence=0.85,
    )
    assert not ev.is_expired

    expired_ev = MobilityEvidence(
        claim="Temporary detour",
        source="Traffic Advisory",
        source_type=MobilitySourceType.TRUSTED_THIRD_PARTY,
        observed_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
        confidence=0.7,
    )
    assert expired_ev.is_expired


def test_mobility_evidence_invalid_confidence():
    with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
        MobilityEvidence(
            claim="Claim",
            source="Source",
            source_type=MobilitySourceType.CALCULATED,
            observed_at=datetime.now(UTC),
            confidence=1.5,
        )


def test_source_hierarchy_ordering():
    assert (
        get_source_hierarchy_weight(MobilitySourceType.OFFICIAL_REALTIME)
        > get_source_hierarchy_weight(MobilitySourceType.OFFICIAL_TIMETABLE)
        > get_source_hierarchy_weight(MobilitySourceType.APPROVED_PROVIDER_API)
        > get_source_hierarchy_weight(MobilitySourceType.TRUSTED_THIRD_PARTY)
        > get_source_hierarchy_weight(MobilitySourceType.CALCULATED)
        > get_source_hierarchy_weight(MobilitySourceType.CROWD_REPORT)
    )
