from datetime import UTC, datetime, time
from decimal import Decimal
import pytest

from app.domain.entities.mobility.enums import (
    BookingCapability,
    MobilityLiveStatus,
    MobilitySourceType,
    TransportMode,
)
from app.domain.entities.mobility.models import MobilityRequirement
from app.infrastructure.mobility.providers.bolt_provider import BoltProvider
from app.infrastructure.mobility.providers.golden_arrow_provider import GoldenArrowProvider
from app.infrastructure.mobility.providers.indrive_provider import InDriveProvider
from app.infrastructure.mobility.providers.myciti_provider import (
    MyCiTiProvider,
    calculate_myciti_fare,
    is_myciti_peak_time,
)
from app.infrastructure.mobility.providers.prasa_provider import PrasaProvider
from app.infrastructure.mobility.providers.uber_provider import UberProvider, build_uber_deeplink
from app.infrastructure.mobility.providers.walking_provider import WalkingProvider


@pytest.mark.asyncio
async def test_walking_provider():
    provider = WalkingProvider()
    assert provider.capability.provider_id == "walking"
    assert provider.capability.supported_modes == [TransportMode.WALK]

    # Walking within reasonable distance (Kloof Street to City Bowl ~ 1-2km)
    req = MobilityRequirement(origin="Kloof Street", destination="City Bowl")
    options = await provider.get_options(req)

    assert len(options) == 1
    opt = options[0]
    assert opt.mode == TransportMode.WALK
    assert opt.cost == Decimal("0")
    assert not opt.cost_is_unknown
    assert opt.duration_minutes is not None and opt.duration_minutes > 0
    assert opt.booking_capability == BookingCapability.NO_BOOKING
    assert opt.source_type == MobilitySourceType.CALCULATED


@pytest.mark.asyncio
async def test_myciti_provider_fare_and_routes():
    provider = MyCiTiProvider()
    assert provider.capability.provider_id == "myciti"
    assert provider.capability.has_realtime is False  # Truthful!

    # Test peak vs off-peak helper
    # Wednesday 07:15 UTC (assume peak)
    dt_weekday_peak = datetime(2026, 9, 30, 7, 15, tzinfo=UTC)
    assert is_myciti_peak_time(dt_weekday_peak) is True

    # Sunday 07:15 (off-peak on weekend)
    dt_weekend = datetime(2026, 10, 4, 7, 15, tzinfo=UTC)
    assert is_myciti_peak_time(dt_weekend) is False

    # Fare band checks
    assert calculate_myciti_fare(3.0, is_peak=False) == Decimal("11.90")
    assert calculate_myciti_fare(3.0, is_peak=True) == Decimal("14.90")
    assert calculate_myciti_fare(15.0, is_peak=True) == Decimal("24.50")
    assert calculate_myciti_fare(15.0, is_peak=False, is_airport=True) == Decimal("115.00")

    # Direct route match: Gardens to Civic Centre (Route 101)
    req = MobilityRequirement(
        origin="Gardens",
        destination="Civic Centre",
        departure_time=dt_weekday_peak,
    )
    options = await provider.get_options(req)
    assert len(options) >= 1
    opt = options[0]
    assert opt.mode == TransportMode.BUS
    assert opt.provider_id == "myciti"
    assert opt.live_status == MobilityLiveStatus.UNKNOWN
    assert opt.cost is not None and opt.cost > 0
    assert opt.source_type == MobilitySourceType.OFFICIAL_TIMETABLE


@pytest.mark.asyncio
async def test_prasa_provider_southern_line():
    provider = PrasaProvider()
    assert provider.capability.provider_id == "prasa_metrorail"
    assert provider.capability.has_realtime is False

    # Southern Line station match: Cape Town to Kalk Bay
    req = MobilityRequirement(origin="Cape Town Station", destination="Kalk Bay")
    options = await provider.get_options(req)

    assert len(options) >= 1
    opt = options[0]
    assert opt.mode == TransportMode.TRAIN
    assert opt.provider_id == "prasa_metrorail"
    assert opt.cost is not None and opt.cost >= Decimal("10.00")
    assert opt.live_status == MobilityLiveStatus.UNKNOWN
    assert opt.source_type == MobilitySourceType.OFFICIAL_TIMETABLE


@pytest.mark.asyncio
async def test_golden_arrow_provider():
    provider = GoldenArrowProvider()
    assert provider.capability.provider_id == "golden_arrow"

    req = MobilityRequirement(origin="Cape Town CBD", destination="Wynberg")
    options = await provider.get_options(req)

    assert len(options) == 1
    opt = options[0]
    assert opt.mode == TransportMode.BUS
    assert opt.cost is None
    assert opt.cost_is_unknown is True
    assert opt.booking_capability == BookingCapability.NO_BOOKING


@pytest.mark.asyncio
async def test_uber_provider_deeplink_and_unknown_fare():
    provider = UberProvider()
    assert provider.capability.provider_id == "uber"
    assert provider.capability.booking_capability == BookingCapability.DEEPLINK

    # Test deeplink construction
    link = build_uber_deeplink(
        destination="V&A Waterfront",
        destination_coords=(-33.9036, 18.4205),
    )
    assert "https://m.uber.com/ul/?action=setPickup" in link
    assert "dropoff%5Bnickname%5D=V%26A+Waterfront" in link
    assert "dropoff%5Blatitude%5D=-33.9036" in link

    # Test query response
    req = MobilityRequirement(origin="Gardens", destination="V&A Waterfront")
    options = await provider.get_options(req)

    assert len(options) == 1
    opt = options[0]
    assert opt.mode == TransportMode.RIDE_HAIL
    assert opt.cost is None
    assert opt.cost_is_unknown is True  # No fake fare!
    assert opt.booking_capability == BookingCapability.DEEPLINK
    assert opt.booking_url is not None and "m.uber.com/ul/" in opt.booking_url
    assert opt.live_status == MobilityLiveStatus.UNKNOWN


@pytest.mark.asyncio
async def test_bolt_and_indrive_providers():
    bolt = BoltProvider()
    indrive = InDriveProvider()

    assert bolt.capability.booking_capability == BookingCapability.EXTERNAL_HANDOFF
    assert indrive.capability.booking_capability == BookingCapability.EXTERNAL_HANDOFF

    req = MobilityRequirement(origin="Gardens", destination="Camps Bay")

    bolt_opts = await bolt.get_options(req)
    assert len(bolt_opts) == 1
    assert bolt_opts[0].cost is None
    assert bolt_opts[0].cost_is_unknown is True
    assert bolt_opts[0].booking_capability == BookingCapability.EXTERNAL_HANDOFF

    indrive_opts = await indrive.get_options(req)
    assert len(indrive_opts) == 1
    assert indrive_opts[0].cost is None
    assert indrive_opts[0].cost_is_unknown is True
    assert indrive_opts[0].booking_capability == BookingCapability.EXTERNAL_HANDOFF
