from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.live_intelligence_service import LiveIntelligenceService
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.adaptation import ItemAction, ItemDiff, PlanAdaptation
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.information import FreshnessKind
from app.domain.entities.planning.live_intelligence import (
    LiveChangeType,
    PlanHealthStatus,
)
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType
from app.infrastructure.planning.live_venue_provider import LiveVenueStatusProvider
from app.infrastructure.planning.live_weather_provider import LiveWeatherProvider, WeatherObservation


def make_test_plan(
    items: list[PlanItem],
    budget_max: Decimal | None = None,
    intention: str = "A day in Cape Town",
) -> Plan:
    plan_id = uuid4()
    user_id = uuid4()
    constraints = []
    if budget_max:
        constraints.append(
            Constraint(
                plan_id=plan_id,
                type=ConstraintType.BUDGET_MAX,
                value=f"R{budget_max}",
                numeric_value=budget_max,
            )
        )

    return Plan(
        id=plan_id,
        user_id=user_id,
        intention=intention,
        title="Cape Town Outing",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, location="Cape Town", start_time=items[0].start_time if items else None),
        constraints=constraints,
        items=items,
    )


# --- Scenario A: No Change ----------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_a_no_change() -> None:
    """Scenario A: Open an existing plan. Refresh live info. Plan still looks good."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 10, 0),
        end_time=datetime(2026, 9, 26, 11, 30),
        estimated_cost=Decimal("75"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock()

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.HEALTHY
    assert result.headline == "Your plan still looks good"
    assert result.proposed_adaptation is None
    mock_adaptation.propose_adaptation.assert_not_called()


# --- Scenario B: Venue Closing Earlier ----------------------------------------
@pytest.mark.asyncio
async def test_scenario_b_venue_closing_earlier() -> None:
    """Scenario B: Museum visit scheduled at 15:00. Live status reports closing at 14:00."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="District Six Museum",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 15, 0),
        end_time=datetime(2026, 9, 26, 16, 30),
        estimated_cost=Decimal("60"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock(
        return_value=PlanAdaptation(
            plan_id=plan.id,
            changes_detected=[],
            narrative_summary="District Six Museum replaced with Iziko SA Museum",
            diffs=[
                ItemDiff(
                    action=ItemAction.REPLACED,
                    original_name="District Six Museum",
                    new_name="Iziko South African National Gallery",
                    reason="Venue closes early",
                )
            ],
        )
    )

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    venue_provider.set_venue_override("District Six Museum", closing_time="14:00")

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "District Six Museum closes at 14:00" in result.narrative
    assert result.proposed_adaptation is not None
    assert result.proposed_adaptation.diffs[0].new_name == "Iziko South African National Gallery"
    # Plan remains unchanged in database until user explicitly accepts
    mock_planning.update_item.assert_not_called()


# --- Scenario C: Weather Change (Outdoor) --------------------------------------
@pytest.mark.asyncio
async def test_scenario_c_weather_change() -> None:
    """Scenario C: Outdoor beach / promenade walk at 14:00. Heavy rain expected."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="Sea Point Promenade Coastal Walk",
        item_type=PlanItemType.ACTIVITY,
        description="Scenic coastal walk along the Atlantic Ocean",
        start_time=datetime(2026, 9, 26, 14, 0),
        end_time=datetime(2026, 9, 26, 15, 30),
        estimated_cost=Decimal("0"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock(
        return_value=PlanAdaptation(
            plan_id=plan.id,
            changes_detected=[],
            narrative_summary="Outdoor promenade replaced with indoor museum due to rain",
            diffs=[
                ItemDiff(
                    action=ItemAction.REPLACED,
                    original_name="Sea Point Promenade Coastal Walk",
                    new_name="Zeitz MOCAA",
                    reason="Outdoor activity unsuitable due to rain",
                )
            ],
        )
    )

    rain_obs = WeatherObservation(
        condition="Heavy Rain",
        precipitation_mm=9.0,
        weather_code=65,
        temperature_c=14.5,
        is_rainy=True,
        freshness=FreshnessKind.LIVE,
    )
    weather_provider = LiveWeatherProvider(mock_observation=rain_obs)
    venue_provider = LiveVenueStatusProvider()

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "Rain is expected" in result.narrative
    assert result.recommended_adaptation_prompt == "nothing outdoors"
    mock_adaptation.propose_adaptation.assert_called_once_with(plan.user_id, plan.id, "nothing outdoors")


# --- Scenario D: Weather Irrelevant (Indoor) -----------------------------------
@pytest.mark.asyncio
async def test_scenario_d_weather_irrelevant() -> None:
    """Scenario D: Indoor museum at 14:00. Rain begins. Plan is NOT changed."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="Zeitz MOCAA Contemporary Art Museum",
        item_type=PlanItemType.ACTIVITY,
        description="Indoor contemporary art gallery in historic grain silo",
        start_time=datetime(2026, 9, 26, 14, 0),
        end_time=datetime(2026, 9, 26, 16, 0),
        estimated_cost=Decimal("250"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock()

    rain_obs = WeatherObservation(
        condition="Rain Showers",
        precipitation_mm=5.0,
        weather_code=80,
        temperature_c=16.0,
        is_rainy=True,
        freshness=FreshnessKind.LIVE,
    )
    weather_provider = LiveWeatherProvider(mock_observation=rain_obs)
    venue_provider = LiveVenueStatusProvider()

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.HEALTHY
    assert result.headline == "Your plan still looks good"
    mock_adaptation.propose_adaptation.assert_not_called()


# --- Scenario E: Event Cancellation -------------------------------------------
@pytest.mark.asyncio
async def test_scenario_e_event_cancellation() -> None:
    """Scenario E: Event item is reported cancelled. Adaptation is proposed."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="The Labia Theatre Film Premiere",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 20, 0),
        end_time=datetime(2026, 9, 26, 22, 0),
        estimated_cost=Decimal("70"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock(
        return_value=PlanAdaptation(
            plan_id=plan.id,
            changes_detected=[],
            narrative_summary="Cancelled event replaced with courtyard drinks",
            diffs=[
                ItemDiff(
                    action=ItemAction.REPLACED,
                    original_name="The Labia Theatre Film Premiere",
                    new_name="Kloof Street House Courtyard Drinks",
                    reason="Event cancelled",
                )
            ],
        )
    )

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    venue_provider.set_venue_override("The Labia Theatre Film Premiere", event_status="cancelled")

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "Event at The Labia Theatre Film Premiere has been cancelled" in result.narrative
    assert result.proposed_adaptation is not None


# --- Scenario F: Provider Failure ---------------------------------------------
@pytest.mark.asyncio
async def test_scenario_f_provider_failure() -> None:
    """Scenario F: Live provider cannot be reached. Safe fallback; plan unchanged."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="Kloof Street House",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 12, 0),
        end_time=datetime(2026, 9, 26, 14, 0),
        estimated_cost=Decimal("280"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock()

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider(simulate_failure=True)

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.HEALTHY
    assert "Your plan still looks good" in result.headline
    mock_adaptation.propose_adaptation.assert_not_called()
    assert any("couldn't refresh" in s.message.lower() for s in result.signals)


# --- Scenario G: Unknown Availability -----------------------------------------
@pytest.mark.asyncio
async def test_scenario_g_unknown_availability() -> None:
    """Scenario G: Provider returns no availability data. Stays unknown; never unavailable."""
    item = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="Maria's Greek Cafe",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 13, 0),
        end_time=datetime(2026, 9, 26, 14, 30),
        estimated_cost=Decimal("190"),
        position=0,
    )
    plan = make_test_plan([item])

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock()

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    venue_provider.set_venue_override("Maria's Greek Cafe", availability="unknown")

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.HEALTHY
    avail_signal = next((s for s in result.signals if s.signal_type.value == "availability"), None)
    assert avail_signal is not None
    assert avail_signal.is_meaningful_change is False
    assert "unknown" in avail_signal.message
    assert "unavailable" not in avail_signal.message.lower().split("not ")[0]


# --- Scenario H: Price Change -------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_h_price_change() -> None:
    """Scenario H: Budget is R600. Verified price increases from R300 to R750. Breaches budget."""
    item1 = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 10, 0),
        end_time=datetime(2026, 9, 26, 11, 0),
        estimated_cost=Decimal("80"),
        position=0,
    )
    item2 = PlanItem(
        id=uuid4(),
        plan_id=uuid4(),
        name="The Pot Luck Club",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 12, 30),
        end_time=datetime(2026, 9, 26, 14, 0),
        estimated_cost=Decimal("380"),
        position=1,
    )
    plan = make_test_plan([item1, item2], budget_max=Decimal("600"))

    mock_planning = MagicMock(spec=PlanningService)
    mock_planning.get_plan = AsyncMock(return_value=plan)

    mock_adaptation = MagicMock(spec=PlanAdaptationService)
    mock_adaptation.propose_adaptation = AsyncMock(
        return_value=PlanAdaptation(
            plan_id=plan.id,
            changes_detected=[],
            narrative_summary="Replaced expensive dining with affordable alternative to stay under R600",
            diffs=[
                ItemDiff(
                    action=ItemAction.REPLACED,
                    original_name="The Pot Luck Club",
                    new_name="Eastern Food Bazaar",
                    reason="Price increase exceeds budget ceiling",
                )
            ],
        )
    )

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    # Price jumps from R380 to R650, which brings total cost to R80 + R650 = R730 > R600
    venue_provider.set_venue_override("The Pot Luck Club", current_price=Decimal("650"))

    service = LiveIntelligenceService(
        planning_service=mock_planning,
        adaptation_service=mock_adaptation,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(plan.user_id, plan.id)

    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "exceeds your budget limit" in result.narrative
    assert "keep it under R600" in result.recommended_adaptation_prompt
    mock_adaptation.propose_adaptation.assert_called_once_with(plan.user_id, plan.id, "keep it under R600")
