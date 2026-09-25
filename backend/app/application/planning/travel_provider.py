from __future__ import annotations

import math
from typing import Protocol

from app.domain.entities.planning.constraints import TravelEstimate, TravelProviderKind


class TravelTimeProvider(Protocol):
    """Clean provider interface for estimating travel time between venues."""

    async def estimate(
        self,
        origin_name: str | None,
        origin_location: str | None,
        destination_name: str | None,
        destination_location: str | None,
    ) -> TravelEstimate:
        ...


class DefaultTravelTimeProvider:
    """Deterministic, provider-agnostic travel time estimator.

    Uses known Cape Town neighborhood transfer matrices when recognizable,
    and falls back to a conservative realistic transit/driving buffer (15 mins)
    clearly flagged as CONSERVATIVE_FALLBACK so uncertainty is never hidden.
    """

    # Approximate transfer minutes between recognizable Cape Town hubs
    _STATIC_MATRIX: dict[tuple[str, str], int] = {
        ("waterfront", "bo-kaap"): 10,
        ("waterfront", "kloof street"): 15,
        ("waterfront", "bree street"): 12,
        ("waterfront", "gardens"): 15,
        ("waterfront", "camps bay"): 25,
        ("waterfront", "sea point"): 12,
        ("bo-kaap", "kloof street"): 8,
        ("bo-kaap", "bree street"): 6,
        ("bo-kaap", "gardens"): 10,
        ("kloof street", "gardens"): 5,
        ("kloof street", "bree street"): 8,
        ("gardens", "bree street"): 7,
    }

    def _normalize_hub(self, text: str | None) -> str | None:
        if not text:
            return None
        lower = text.lower()
        if "waterfront" in lower or "v&a" in lower or "harbour" in lower:
            return "waterfront"
        if "bo-kaap" in lower or "bokaap" in lower:
            return "bo-kaap"
        if "kloof" in lower:
            return "kloof street"
        if "bree" in lower:
            return "bree street"
        if "gardens" in lower or "company gardens" in lower:
            return "gardens"
        if "camps bay" in lower:
            return "camps bay"
        if "sea point" in lower:
            return "sea point"
        return None

    async def estimate(
        self,
        origin_name: str | None,
        origin_location: str | None,
        destination_name: str | None,
        destination_location: str | None,
    ) -> TravelEstimate:
        hub_a = self._normalize_hub(origin_name) or self._normalize_hub(origin_location)
        hub_b = self._normalize_hub(destination_name) or self._normalize_hub(destination_location)

        if hub_a and hub_b:
            if hub_a == hub_b:
                return TravelEstimate(
                    origin=origin_name or origin_location,
                    destination=destination_name or destination_location,
                    duration_minutes=5,
                    provider_kind=TravelProviderKind.STATIC_ESTIMATE,
                    confidence="verified",
                )
            key = (hub_a, hub_b)
            rev_key = (hub_b, hub_a)
            if key in self._STATIC_MATRIX:
                return TravelEstimate(
                    origin=origin_name or origin_location,
                    destination=destination_name or destination_location,
                    duration_minutes=self._STATIC_MATRIX[key],
                    provider_kind=TravelProviderKind.STATIC_ESTIMATE,
                    confidence="estimated",
                )
            if rev_key in self._STATIC_MATRIX:
                return TravelEstimate(
                    origin=origin_name or origin_location,
                    destination=destination_name or destination_location,
                    duration_minutes=self._STATIC_MATRIX[rev_key],
                    provider_kind=TravelProviderKind.STATIC_ESTIMATE,
                    confidence="estimated",
                )

        # Default conservative city transit buffer
        return TravelEstimate(
            origin=origin_name or origin_location,
            destination=destination_name or destination_location,
            duration_minutes=15,
            provider_kind=TravelProviderKind.CONSERVATIVE_FALLBACK,
            confidence="fallback",
        )
