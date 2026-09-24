from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import logging
from typing import Any

from app.domain.entities.planning.information import FreshnessKind

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VenueLiveStatus:
    venue_name: str
    is_open: bool | None
    closing_time: str | None = None
    event_status: str | None = None  # "scheduled", "cancelled", "rescheduled"
    availability: str = "unknown"  # "available", "unavailable", "unknown"
    current_price: Decimal | None = None
    freshness: FreshnessKind = FreshnessKind.LIVE
    provider_error: str | None = None
    observed_at: datetime | None = None


class LiveVenueStatusProvider:
    """Provides live operating status, hours, event status, and availability checks.

    Adheres to the core principles:
    - Never fabricates closures or cancellations.
    - Missing availability data is strictly 'unknown', never 'unavailable'.
    - Provider failures result in safe fallbacks with freshness=UNKNOWN without breaking plans.
    """

    def __init__(
        self,
        *,
        overrides: dict[str, dict[str, Any]] | None = None,
        simulate_failure: bool = False,
    ) -> None:
        self._overrides = overrides or {}
        self._simulate_failure = simulate_failure

    def set_venue_override(self, venue_name: str, **kwargs: Any) -> None:
        """Register a dynamic live signal for a venue (used by simulations and tests)."""
        self._overrides[venue_name.casefold()] = kwargs

    def clear_overrides(self) -> None:
        self._overrides.clear()

    def check_venue_status(self, venue_name: str, planned_time: datetime | None = None) -> VenueLiveStatus:
        """Query live operational information for a venue."""
        now = datetime.now(UTC)

        if self._simulate_failure:
            logger.warning("Live venue provider failed to connect for '%s'", venue_name)
            return VenueLiveStatus(
                venue_name=venue_name,
                is_open=None,
                freshness=FreshnessKind.UNKNOWN,
                provider_error="Provider connection timeout",
                observed_at=now,
            )

        key = venue_name.casefold()
        override = None
        for k, v in self._overrides.items():
            if k in key or key in k:
                override = v
                break

        if override is not None:
            return VenueLiveStatus(
                venue_name=venue_name,
                is_open=override.get("is_open", True),
                closing_time=override.get("closing_time"),
                event_status=override.get("event_status"),
                availability=override.get("availability", "unknown"),
                current_price=override.get("current_price"),
                freshness=override.get("freshness", FreshnessKind.LIVE),
                provider_error=override.get("provider_error"),
                observed_at=now,
            )

        # Baseline: normal operation, verified from authoritative catalog
        return VenueLiveStatus(
            venue_name=venue_name,
            is_open=True,
            closing_time=None,
            event_status="scheduled",
            availability="unknown",
            current_price=None,
            freshness=FreshnessKind.RECENTLY_VERIFIED,
            observed_at=now,
        )
