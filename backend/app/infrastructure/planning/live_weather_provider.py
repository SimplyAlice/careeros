from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from app.domain.entities.planning.information import FreshnessKind

logger = logging.getLogger(__name__)

# WMO Weather Codes that indicate adverse/wet weather
RAIN_WEATHER_CODES = {
    51, 53, 55, 56, 57,  # Drizzle
    61, 63, 65, 66, 67,  # Rain
    71, 73, 75, 77,      # Snow
    80, 81, 82,          # Rain showers
    85, 86,              # Snow showers
    95, 96, 99,          # Thunderstorm
}


@dataclass(frozen=True)
class WeatherObservation:
    condition: str
    precipitation_mm: float
    weather_code: int
    temperature_c: float
    is_rainy: bool
    freshness: FreshnessKind
    source: str = "open-meteo"
    observed_at: datetime | None = None


class LiveWeatherProvider:
    """Queries Open-Meteo for live and forecasted weather in Cape Town.

    Free, open API, zero credentials needed.
    Implements a strict 2.0s timeout and safe fallback handling.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 2.0,
        enable_network: bool = True,
        mock_observation: WeatherObservation | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._enable_network = enable_network
        self._mock_observation = mock_observation

    def get_weather_for_time(
        self,
        target_time: datetime,
        latitude: float = -33.9249,
        longitude: float = 18.4241,
    ) -> WeatherObservation:
        """Retrieve weather observation for specific coordinate and time."""
        if self._mock_observation is not None:
            return self._mock_observation

        if not self._enable_network:
            return WeatherObservation(
                condition="Clear",
                precipitation_mm=0.0,
                weather_code=0,
                temperature_c=20.0,
                is_rainy=False,
                freshness=FreshnessKind.RECENTLY_VERIFIED,
                observed_at=datetime.now(UTC),
            )

        try:
            params = urllib.parse.urlencode({
                "latitude": f"{latitude:.4f}",
                "longitude": f"{longitude:.4f}",
                "hourly": "precipitation,weathercode,temperature_2m",
                "timezone": "Africa/Johannesburg",
            })
            url = f"https://api.open-meteo.com/v1/forecast?{params}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Dayform-LiveIntelligence/0.1 (careeros-clean; dev@dayform.local)"}
            )
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                precipitations = hourly.get("precipitation", [])
                weathercodes = hourly.get("weathercode", [])
                temperatures = hourly.get("temperature_2m", [])

                target_iso = target_time.strftime("%Y-%m-%dT%H:00")
                match_idx = 0
                if target_iso in times:
                    match_idx = times.index(target_iso)
                elif times:
                    match_idx = 0

                precip = float(precipitations[match_idx]) if match_idx < len(precipitations) else 0.0
                code = int(weathercodes[match_idx]) if match_idx < len(weathercodes) else 0
                temp = float(temperatures[match_idx]) if match_idx < len(temperatures) else 20.0

                is_rainy = code in RAIN_WEATHER_CODES or precip >= 1.0
                condition = "Rain / Storm" if is_rainy else "Clear / Mild"

                return WeatherObservation(
                    condition=condition,
                    precipitation_mm=precip,
                    weather_code=code,
                    temperature_c=temp,
                    is_rainy=is_rainy,
                    freshness=FreshnessKind.LIVE,
                    observed_at=datetime.now(UTC),
                )
        except Exception as exc:
            logger.warning("Live weather query to Open-Meteo failed (%s). Failing safely.", exc)
            return WeatherObservation(
                condition="Unknown",
                precipitation_mm=0.0,
                weather_code=0,
                temperature_c=20.0,
                is_rainy=False,
                freshness=FreshnessKind.UNKNOWN,
                observed_at=datetime.now(UTC),
            )
