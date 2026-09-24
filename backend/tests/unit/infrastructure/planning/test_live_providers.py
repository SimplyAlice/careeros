from datetime import UTC, datetime
from decimal import Decimal

from app.domain.entities.planning.information import FreshnessKind
from app.infrastructure.planning.live_venue_provider import LiveVenueStatusProvider
from app.infrastructure.planning.live_weather_provider import LiveWeatherProvider, WeatherObservation


def test_weather_provider_network_disabled() -> None:
    provider = LiveWeatherProvider(enable_network=False)
    obs = provider.get_weather_for_time(datetime.now(UTC))
    assert obs.is_rainy is False
    assert obs.condition == "Clear"
    assert obs.freshness is FreshnessKind.RECENTLY_VERIFIED


def test_weather_provider_mock_observation() -> None:
    mock_obs = WeatherObservation(
        condition="Heavy Thunderstorm",
        precipitation_mm=12.5,
        weather_code=95,
        temperature_c=16.0,
        is_rainy=True,
        freshness=FreshnessKind.LIVE,
    )
    provider = LiveWeatherProvider(mock_observation=mock_obs)
    obs = provider.get_weather_for_time(datetime.now(UTC))
    assert obs.is_rainy is True
    assert obs.condition == "Heavy Thunderstorm"
    assert obs.precipitation_mm == 12.5


def test_weather_provider_handles_exception_safely() -> None:
    provider = LiveWeatherProvider(enable_network=True, timeout_seconds=0.001)
    # Target invalid address/timeout to force graceful exception handler
    obs = provider.get_weather_for_time(datetime.now(UTC), latitude=-999.0, longitude=-999.0)
    assert obs.freshness is FreshnessKind.UNKNOWN
    assert obs.condition == "Unknown"
    assert obs.is_rainy is False


def test_venue_provider_baseline() -> None:
    provider = LiveVenueStatusProvider()
    status = provider.check_venue_status("Kirstenbosch")
    assert status.is_open is True
    assert status.availability == "unknown"
    assert status.provider_error is None
    assert status.freshness is FreshnessKind.RECENTLY_VERIFIED


def test_venue_provider_override() -> None:
    provider = LiveVenueStatusProvider()
    provider.set_venue_override(
        "Kirstenbosch",
        is_open=False,
        closing_time="14:00",
        availability="unavailable",
        current_price=Decimal("150"),
        freshness=FreshnessKind.LIVE,
    )
    status = provider.check_venue_status("Kirstenbosch National Botanical Garden")
    assert status.is_open is False
    assert status.closing_time == "14:00"
    assert status.availability == "unavailable"
    assert status.current_price == Decimal("150")
    assert status.freshness is FreshnessKind.LIVE


def test_venue_provider_simulate_failure() -> None:
    provider = LiveVenueStatusProvider(simulate_failure=True)
    status = provider.check_venue_status("Truth Coffee")
    assert status.is_open is None
    assert status.freshness is FreshnessKind.UNKNOWN
    assert status.provider_error == "Provider connection timeout"
