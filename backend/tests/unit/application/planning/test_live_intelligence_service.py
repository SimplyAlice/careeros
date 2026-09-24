from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.live_intelligence_service import LiveIntelligenceService
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.adaptation import PlanAdaptation
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


@pytest.fixture
def mock_planning_service() -> MagicMock:
    service = MagicMock(spec=PlanningService)
    service.get_plan = AsyncMock()
    return service


@pytest.fixture
def mock_adaptation_service() -> MagicMock:
    service = MagicMock(spec=PlanAdaptationService)
    service.propose_adaptation = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_health_check_clean_plan(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 11, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Coffee and gallery",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="Truth Coffee Roasting",
                item_type=PlanItemType.FOOD,
                start_time=datetime(2026, 9, 26, 11, 0),
                end_time=datetime(2026, 9, 26, 12, 0),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    assert result.health_status is PlanHealthStatus.HEALTHY
    assert result.headline == "Your plan still looks good"
    assert result.proposed_adaptation is None


@pytest.mark.asyncio
async def test_health_check_outdoor_rain_triggers_adaptation(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 14, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Walk in Kirstenbosch Garden",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="Kirstenbosch National Botanical Garden",
                item_type=PlanItemType.ACTIVITY,
                start_time=datetime(2026, 9, 26, 14, 0),
                end_time=datetime(2026, 9, 26, 16, 0),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    rain_obs = WeatherObservation(
        condition="Heavy Rain",
        precipitation_mm=8.5,
        weather_code=63,
        temperature_c=15.0,
        is_rainy=True,
        freshness=FreshnessKind.LIVE,
    )
    weather_provider = LiveWeatherProvider(mock_observation=rain_obs)
    venue_provider = LiveVenueStatusProvider()

    mock_adaptation_service.propose_adaptation.return_value = PlanAdaptation(
        plan_id=plan_id,
        changes_detected=[],
        narrative_summary="Indoor alternatives found",
        diffs=[],
    )

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "Rain is expected" in result.narrative
    assert result.recommended_adaptation_prompt == "nothing outdoors"
    mock_adaptation_service.propose_adaptation.assert_called_once_with(user_id, plan_id, "nothing outdoors")


@pytest.mark.asyncio
async def test_health_check_indoor_venue_ignores_rain(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 14, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Art museum visit",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="Zeitz MOCAA",
                item_type=PlanItemType.ACTIVITY,
                start_time=datetime(2026, 9, 26, 14, 0),
                end_time=datetime(2026, 9, 26, 16, 0),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    rain_obs = WeatherObservation(
        condition="Heavy Rain",
        precipitation_mm=8.5,
        weather_code=63,
        temperature_c=15.0,
        is_rainy=True,
        freshness=FreshnessKind.LIVE,
    )
    weather_provider = LiveWeatherProvider(mock_observation=rain_obs)
    venue_provider = LiveVenueStatusProvider()

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    assert result.health_status is PlanHealthStatus.HEALTHY
    assert result.headline == "Your plan still looks good"
    mock_adaptation_service.propose_adaptation.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_venue_closing_early(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 15, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Museum afternoon",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="District Six Museum",
                item_type=PlanItemType.ACTIVITY,
                start_time=datetime(2026, 9, 26, 15, 0),
                end_time=datetime(2026, 9, 26, 16, 30),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    venue_provider.set_venue_override("District Six Museum", closing_time="14:00")

    mock_adaptation_service.propose_adaptation.return_value = PlanAdaptation(
        plan_id=plan_id,
        changes_detected=[],
        narrative_summary="Rescheduled or alternative found",
        diffs=[],
    )

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "District Six Museum closes at 14:00" in result.narrative
    assert "District Six Museum is closed" in result.recommended_adaptation_prompt


@pytest.mark.asyncio
async def test_health_check_event_cancelled(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 19, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Evening concert",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="The Labia Theatre",
                item_type=PlanItemType.ACTIVITY,
                start_time=datetime(2026, 9, 26, 19, 0),
                end_time=datetime(2026, 9, 26, 21, 0),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    venue_provider.set_venue_override("The Labia Theatre", event_status="cancelled")

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    assert result.health_status is PlanHealthStatus.ACTION_REQUIRED
    assert "Event at The Labia Theatre has been cancelled." in result.narrative


@pytest.mark.asyncio
async def test_health_check_provider_failure_fails_safely(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 11, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Coffee at Truth",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="Truth Coffee Roasting",
                item_type=PlanItemType.FOOD,
                start_time=datetime(2026, 9, 26, 11, 0),
                end_time=datetime(2026, 9, 26, 12, 0),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider(simulate_failure=True)

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    # Provider failure should fail safely: plan is healthy/unchanged, no adaptation triggered
    assert result.health_status is PlanHealthStatus.HEALTHY
    mock_adaptation_service.propose_adaptation.assert_not_called()
    assert any("Could not refresh" in s.message or "couldn't refresh" in s.message for s in result.signals)


@pytest.mark.asyncio
async def test_health_check_unknown_availability_preservation(mock_planning_service, mock_adaptation_service) -> None:
    user_id = uuid4()
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 12, 0)

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Lunch",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, start_time=now),
        items=[
            PlanItem(
                id=uuid4(),
                plan_id=plan_id,
                name="Kloof Street House",
                item_type=PlanItemType.FOOD,
                start_time=datetime(2026, 9, 26, 12, 0),
                end_time=datetime(2026, 9, 26, 14, 0),
                position=0,
            )
        ],
    )
    mock_planning_service.get_plan.return_value = plan

    weather_provider = LiveWeatherProvider(enable_network=False)
    venue_provider = LiveVenueStatusProvider()
    venue_provider.set_venue_override("Kloof Street House", availability="unknown")

    service = LiveIntelligenceService(
        planning_service=mock_planning_service,
        adaptation_service=mock_adaptation_service,
        weather_provider=weather_provider,
        venue_provider=venue_provider,
    )

    result = await service.check_plan_health(user_id, plan_id)
    assert result.health_status is PlanHealthStatus.HEALTHY
    avail_signal = next((s for s in result.signals if s.signal_type.value == "availability"), None)
    assert avail_signal is not None
    assert avail_signal.is_meaningful_change is False
    assert "unknown" in avail_signal.message
