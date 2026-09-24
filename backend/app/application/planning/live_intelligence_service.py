from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import logging
import re
from typing import Any
from uuid import UUID

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.information import FreshnessKind
from app.domain.entities.planning.live_intelligence import (
    LiveChangeType,
    LiveSignal,
    LiveSignalType,
    PlanHealthCheckResult,
    PlanHealthStatus,
)
from app.domain.entities.planning.plan import Plan
from app.domain.entities.planning.plan_item import PlanItem
from app.infrastructure.planning.live_venue_provider import LiveVenueStatusProvider
from app.infrastructure.planning.live_weather_provider import LiveWeatherProvider

logger = logging.getLogger(__name__)

OUTDOOR_KEYWORDS = (
    "kirstenbosch",
    "table mountain",
    "lion's head",
    "promenade",
    "botanical",
    "hike",
    "trail",
    "beach",
    "park",
    "garden",
    "coastal",
    "boomslang",
)


class LiveIntelligenceService:
    """Monitors and evaluates live signals pertinent to an approved plan.

    Grounded in the Core Principles:
    - Detect only changes that matter to the user's current plan.
    - Weather changes affect outdoor activities, but are ignored for indoor stops.
    - Missing availability data is strictly 'unknown', never 'unavailable'.
    - Provider failures fail safely without claiming closures or mutating plans.
    - When meaningful changes occur, generates an adaptation proposal via M5 PlanAdaptationService
      for user review without silent plan rewrites.
    """

    def __init__(
        self,
        planning_service: PlanningService,
        adaptation_service: PlanAdaptationService,
        weather_provider: LiveWeatherProvider | None = None,
        venue_provider: LiveVenueStatusProvider | None = None,
    ) -> None:
        self._planning_service = planning_service
        self._adaptation_service = adaptation_service
        self._weather_provider = weather_provider or LiveWeatherProvider()
        self._venue_provider = venue_provider or LiveVenueStatusProvider()

    async def check_plan_health(self, user_id: UUID, plan_id: UUID) -> PlanHealthCheckResult:
        """Evaluate real-world signals for all stops in the plan."""
        plan = await self._planning_service.get_plan(user_id, plan_id)
        now = datetime.now(UTC)

        signals: list[LiveSignal] = []
        meaningful_changes: list[LiveSignal] = []

        # Sort items chronologically / by position
        items = list(plan.items)
        items.sort(key=lambda i: i.position)

        for item in items:
            item_signals = self._evaluate_item_signals(item, plan, now)
            signals.extend(item_signals)
            for s in item_signals:
                if s.is_meaningful_change:
                    meaningful_changes.append(s)

        # Plan-level evaluation
        if not meaningful_changes:
            return PlanHealthCheckResult(
                plan_id=plan.id,
                health_status=PlanHealthStatus.HEALTHY,
                headline="Your plan still looks good",
                narrative="All venues verified open and weather conditions are suitable for your scheduled stops.",
                signals=signals,
                checked_at=now,
                recommended_adaptation_prompt=None,
                proposed_adaptation=None,
            )

        # Action is required: synthesize human explanation and adaptation prompt
        headline = (
            f"Something changed ({len(meaningful_changes)} "
            f"{'update' if len(meaningful_changes) == 1 else 'updates'} detected)"
        )
        narrative_parts = [s.message for s in meaningful_changes]
        narrative = " ".join(narrative_parts)

        adaptation_prompt = self._build_adaptation_prompt(meaningful_changes, plan)

        # Generate proposed adaptation via M5 PlanAdaptationService for user review
        proposed_adaptation = None
        try:
            proposed_adaptation = await self._adaptation_service.propose_adaptation(
                user_id, plan.id, adaptation_prompt
            )
        except Exception as exc:
            logger.warning("Could not automatically formulate proposed adaptation: %s", exc)

        return PlanHealthCheckResult(
            plan_id=plan.id,
            health_status=PlanHealthStatus.ACTION_REQUIRED,
            headline=headline,
            narrative=narrative,
            signals=signals,
            checked_at=now,
            recommended_adaptation_prompt=adaptation_prompt,
            proposed_adaptation=proposed_adaptation,
        )

    def _evaluate_item_signals(
        self, item: PlanItem, plan: Plan, now: datetime
    ) -> list[LiveSignal]:
        signals: list[LiveSignal] = []
        is_outdoor = self._is_outdoor_item(item)
        target_time = item.start_time or now

        # 1. Weather Signal
        weather = self._weather_provider.get_weather_for_time(target_time)
        if weather.freshness is FreshnessKind.UNKNOWN:
            signals.append(
                LiveSignal(
                    source="open-meteo",
                    signal_type=LiveSignalType.WEATHER,
                    observed_at=now,
                    freshness=FreshnessKind.UNKNOWN,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.INFORMATIONAL,
                    is_meaningful_change=False,
                    message="Weather service currently unreachable. Existing plan is unchanged.",
                )
            )
        elif is_outdoor:
            if weather.is_rainy:
                signals.append(
                    LiveSignal(
                        source="open-meteo",
                        signal_type=LiveSignalType.WEATHER,
                        observed_at=now,
                        freshness=FreshnessKind.LIVE,
                        target_name=item.name,
                        target_item_id=item.id,
                        change_type=LiveChangeType.WEATHER_UNSUITABLE,
                        current_value={"condition": weather.condition, "precip_mm": weather.precipitation_mm},
                        is_meaningful_change=True,
                        message=f"Rain is expected during your outdoor activity at {item.name}.",
                    )
                )
            else:
                signals.append(
                    LiveSignal(
                        source="open-meteo",
                        signal_type=LiveSignalType.WEATHER,
                        observed_at=now,
                        freshness=FreshnessKind.LIVE,
                        target_name=item.name,
                        target_item_id=item.id,
                        change_type=LiveChangeType.NONE,
                        current_value={"condition": weather.condition},
                        is_meaningful_change=False,
                        message=f"Weather clear for {item.name}.",
                    )
                )
        else:
            # Indoor venue: weather is irrelevant!
            signals.append(
                LiveSignal(
                    source="open-meteo",
                    signal_type=LiveSignalType.WEATHER,
                    observed_at=now,
                    freshness=weather.freshness,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.NONE,
                    current_value={"condition": weather.condition, "indoor": True},
                    is_meaningful_change=False,
                    message=f"{item.name} is an indoor venue; weather forecast does not affect this visit.",
                )
            )

        # 2. Operating Status & Hours Signal
        venue_status = self._venue_provider.check_venue_status(item.name, item.start_time)
        if venue_status.provider_error:
            signals.append(
                LiveSignal(
                    source="venue_status_provider",
                    signal_type=LiveSignalType.VENUE_STATUS,
                    observed_at=now,
                    freshness=FreshnessKind.UNKNOWN,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.INFORMATIONAL,
                    is_meaningful_change=False,
                    message=f"I couldn't refresh information for {item.name} right now. Your existing plan is unchanged.",
                )
            )
        elif venue_status.is_open is False:
            signals.append(
                LiveSignal(
                    source="venue_status_provider",
                    signal_type=LiveSignalType.VENUE_STATUS,
                    observed_at=now,
                    freshness=venue_status.freshness,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.VENUE_CLOSED,
                    current_value={"status": "closed"},
                    is_meaningful_change=True,
                    message=f"{item.name} is reported closed.",
                )
            )
        elif venue_status.closing_time:
            # Check for temporal conflict with scheduled stop
            closing_h, closing_m = map(int, venue_status.closing_time.split(":"))
            scheduled_start_h = item.start_time.hour if item.start_time else 15
            scheduled_end_h = item.end_time.hour if item.end_time else (scheduled_start_h + 1)

            if closing_h <= scheduled_start_h or (closing_h == scheduled_end_h and venue_status.closing_time < (item.end_time.strftime("%H:%M") if item.end_time else "16:00")):
                signals.append(
                    LiveSignal(
                        source="venue_status_provider",
                        signal_type=LiveSignalType.OPERATING_HOURS,
                        observed_at=now,
                        freshness=venue_status.freshness,
                        target_name=item.name,
                        target_item_id=item.id,
                        change_type=LiveChangeType.CLOSING_EARLY,
                        current_value={"closing_time": venue_status.closing_time},
                        is_meaningful_change=True,
                        message=f"{item.name} closes at {venue_status.closing_time}, before your planned visit.",
                    )
                )

        # 3. Event Status Signal
        if venue_status.event_status == "cancelled":
            signals.append(
                LiveSignal(
                    source="event_status_provider",
                    signal_type=LiveSignalType.EVENT_STATUS,
                    observed_at=now,
                    freshness=venue_status.freshness,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.EVENT_CANCELLED,
                    current_value={"event_status": "cancelled"},
                    is_meaningful_change=True,
                    message=f"Event at {item.name} has been cancelled.",
                )
            )

        # 4. Availability Signal (Honest three-state: available, unavailable, unknown)
        if venue_status.availability == "unavailable":
            signals.append(
                LiveSignal(
                    source="availability_provider",
                    signal_type=LiveSignalType.AVAILABILITY,
                    observed_at=now,
                    freshness=venue_status.freshness,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.CAPACITY_UNAVAILABLE,
                    current_value={"availability": "unavailable"},
                    is_meaningful_change=True,
                    message=f"{item.name} has no availability remaining.",
                )
            )
        elif venue_status.availability == "unknown":
            signals.append(
                LiveSignal(
                    source="availability_provider",
                    signal_type=LiveSignalType.AVAILABILITY,
                    observed_at=now,
                    freshness=venue_status.freshness,
                    target_name=item.name,
                    target_item_id=item.id,
                    change_type=LiveChangeType.NONE,
                    current_value={"availability": "unknown"},
                    is_meaningful_change=False,
                    message=f"Availability for {item.name} is unknown (treated safely as unconfirmed, not unavailable).",
                )
            )

        # 5. Price Signal (material price change affecting budget)
        if venue_status.current_price is not None and item.estimated_cost is not None:
            price_delta = venue_status.current_price - item.estimated_cost
            if price_delta > Decimal("0"):
                # Check if total planned cost exceeds maximum budget
                budget_summary = plan.budget_summary()
                budget_max = budget_summary.budget_maximum
                current_total = budget_summary.total_planned_cost
                new_total = current_total + price_delta

                if budget_max is not None and new_total > budget_max:
                    signals.append(
                        LiveSignal(
                            source="price_feed",
                            signal_type=LiveSignalType.PRICE,
                            observed_at=now,
                            freshness=venue_status.freshness,
                            target_name=item.name,
                            target_item_id=item.id,
                            change_type=LiveChangeType.PRICE_BUDGET_OVERAGE,
                            current_value={"price": venue_status.current_price},
                            previous_value={"price": item.estimated_cost},
                            is_meaningful_change=True,
                            message=f"Price for {item.name} increased to R{venue_status.current_price:.0f}, which exceeds your budget limit of R{budget_max:.0f}.",
                        )
                    )

        return signals

    def _is_outdoor_item(self, item: PlanItem) -> bool:
        """Determines whether a stop is outdoors or weather-sensitive."""
        name_lower = item.name.lower()
        desc_lower = (item.description or "").lower()
        return any(k in name_lower or k in desc_lower for k in OUTDOOR_KEYWORDS)

    def _build_adaptation_prompt(self, changes: list[LiveSignal], plan: Plan) -> str:
        """Formulate a minimal, natural-language prompt for M5 PlanAdaptationService."""
        prompts: list[str] = []

        for change in changes:
            if change.change_type is LiveChangeType.WEATHER_UNSUITABLE:
                prompts.append("nothing outdoors")
            elif change.change_type in (
                LiveChangeType.VENUE_CLOSED,
                LiveChangeType.CLOSING_EARLY,
                LiveChangeType.EVENT_CANCELLED,
                LiveChangeType.CAPACITY_UNAVAILABLE,
            ):
                prompts.append(f"{change.target_name} is closed")
            elif change.change_type is LiveChangeType.PRICE_BUDGET_OVERAGE:
                budget_summary = plan.budget_summary()
                budget_max = budget_summary.budget_maximum or Decimal("600")
                prompts.append(f"keep it under R{budget_max:.0f}")

        # Combine into cohesive prompt
        return "; ".join(prompts) if prompts else "something changed"
