from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.information import PlanningInformationService
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.adaptation import ChangeType, ItemAction
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.decision import (
    CandidateType,
    DecisionCandidate,
    DecisionReason,
    DecisionResult,
    ReasonOutcome,
    ReasonType,
)
from app.domain.entities.planning.information import InformationCategory, InformationSource
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


@pytest.fixture
def mock_planning_service() -> MagicMock:
    service = MagicMock(spec=PlanningService)
    service.get_plan = AsyncMock()
    service.delete_item = AsyncMock()
    service.add_item = AsyncMock()
    service._repository = MagicMock()
    service._repository.update = AsyncMock()
    return service


@pytest.fixture
def mock_decision_service() -> MagicMock:
    service = MagicMock(spec=PlanningDecisionService)
    service.recommend = AsyncMock()
    return service


@pytest.fixture
def mock_info_service() -> MagicMock:
    service = MagicMock(spec=PlanningInformationService)
    service.source = InformationSource(
        data_source="fixture",
        is_live=False,
        attribution=None,
        freshness="fixture",
    )
    return service


def test_detect_changes_time_shift(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Date in Cape Town",
        context=PlanningContext(plan_id=uuid4(), start_time=datetime(2026, 9, 26, 11, 0)),
        constraints=[],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "Actually we can only leave at 2")
    assert ChangeType.TIME_SHIFT in changes
    assert ctx.start_time.hour == 14
    assert ctx.start_time.minute == 0


def test_detect_changes_budget_reduction(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Date in Cape Town",
        constraints=[Constraint(plan_id=uuid4(), type=ConstraintType.BUDGET_MAX, value="R1000", numeric_value=Decimal("1000"))],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "Actually keep it under R600")
    assert ChangeType.BUDGET_REDUCED in changes
    assert details["budget_max"] == Decimal("600")


def test_detect_changes_group_size(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Outing in Cape Town",
        context=PlanningContext(plan_id=uuid4(), group_size=2),
        constraints=[Constraint(plan_id=uuid4(), type=ConstraintType.GROUP_SIZE, value="2", numeric_value=Decimal("2"))],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "Actually two more friends are coming")
    assert ChangeType.GROUP_SIZE_CHANGED in changes
    assert ctx.group_size == 4


def test_detect_changes_exclusion(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Day out",
        constraints=[],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "Actually nothing outdoors")
    assert ChangeType.EXCLUSION_ADDED in changes
    assert details["exclude_outdoors"] is True
    assert any(c.value == "exclude:no_outdoors" for c in constraints)


def test_detect_changes_closed_venue(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Coffee and walk",
        constraints=[],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "Truth Coffee is closed")
    assert ChangeType.VENUE_INVALIDATED in changes
    assert details["closed_venue_name"] == "truth coffee"


def test_detect_changes_location(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Saturday day out",
        context=PlanningContext(plan_id=uuid4(), location="City Bowl"),
        constraints=[],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "Actually let's do Camps Bay")
    assert ChangeType.LOCATION_CHANGED in changes
    assert ctx.location == "Camps Bay"


def test_detect_changes_duration_limit(mock_planning_service, mock_decision_service, mock_info_service) -> None:
    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    plan = Plan(
        id=uuid4(),
        user_id=uuid4(),
        intention="Quick outing",
        constraints=[],
    )

    ctx, constraints, changes, details = service._detect_changes(plan, "I only have one hour")
    assert ChangeType.DURATION_LIMIT_CHANGED in changes
    assert details["duration_limit_minutes"] == 60


@pytest.mark.asyncio
async def test_propose_adaptation_scenario_a_later_start(
    mock_planning_service, mock_decision_service, mock_info_service
) -> None:
    plan_id = uuid4()
    user_id = uuid4()

    item1 = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 0),
        estimated_cost=Decimal("150"),
        position=0,
    )
    item2 = PlanItem(
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 15),
        end_time=datetime(2026, 9, 26, 14, 0),
        estimated_cost=Decimal("250"),
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Date in Cape Town",
        context=PlanningContext(plan_id=plan_id, start_time=datetime(2026, 9, 26, 11, 0)),
        items=[item1, item2],
    )
    mock_planning_service.get_plan.return_value = plan
    mock_decision_service.recommend.return_value = DecisionResult(candidates=(), source="fixture", is_live=False, attribution=None, freshness="fixture")

    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    adaptation = await service.propose_adaptation(user_id, plan_id, "Actually we can only leave at 2")

    assert ChangeType.TIME_SHIFT in adaptation.changes_detected
    assert len(adaptation.adapted_items) == 2
    assert adaptation.adapted_items[0].start_time.hour == 14
    assert adaptation.diffs[0].action is ItemAction.RESCHEDULED
    assert adaptation.diffs[1].action is ItemAction.RESCHEDULED


@pytest.mark.asyncio
async def test_propose_adaptation_scenario_d_exclusion(
    mock_planning_service, mock_decision_service, mock_info_service
) -> None:
    plan_id = uuid4()
    user_id = uuid4()

    item_food = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 0),
        estimated_cost=Decimal("150"),
        position=0,
    )
    item_outdoor = PlanItem(
        plan_id=plan_id,
        name="Kirstenbosch National Botanical Garden",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 30),
        end_time=datetime(2026, 9, 26, 14, 30),
        estimated_cost=Decimal("220"),
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Date in Cape Town",
        context=PlanningContext(plan_id=plan_id, start_time=datetime(2026, 9, 26, 11, 0)),
        items=[item_food, item_outdoor],
    )
    mock_planning_service.get_plan.return_value = plan

    # Indoor replacement candidate
    museum_cand = DecisionCandidate(
        option_id=uuid4(),
        option_type=CandidateType.ACTIVITY,
        name="Iziko South African Museum",
        is_eligible=True,
        score=100,
        reasons=(
            DecisionReason(
                type=ReasonType.PREFERENCE,
                outcome=ReasonOutcome.SUPPORTED,
                message="Indoor cultural attraction",
            ),
        ),
        category=InformationCategory.CULTURE,
        cost=Decimal("100"),
        duration_minutes=90,
        location="Company's Garden, Cape Town",
    )
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(museum_cand,), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    adaptation = await service.propose_adaptation(user_id, plan_id, "Actually nothing outdoors")

    assert ChangeType.EXCLUSION_ADDED in adaptation.changes_detected
    assert len(adaptation.adapted_items) == 2
    # Item 0 (Truth Coffee) is kept
    assert adaptation.diffs[0].action in (ItemAction.KEPT, ItemAction.RESCHEDULED)
    assert adaptation.diffs[0].original_name == "Truth Coffee"
    # Item 1 (Kirstenbosch) is replaced with Iziko Museum
    assert adaptation.diffs[1].action is ItemAction.REPLACED
    assert adaptation.diffs[1].original_name == "Kirstenbosch National Botanical Garden"
    assert adaptation.diffs[1].new_name == "Iziko South African Museum"


@pytest.mark.asyncio
async def test_propose_adaptation_scenario_g_impossible_window_scales_down(
    mock_planning_service, mock_decision_service, mock_info_service
) -> None:
    plan_id = uuid4()
    user_id = uuid4()

    item1 = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 0),
        estimated_cost=Decimal("150"),
        position=0,
    )
    item2 = PlanItem(
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 15),
        end_time=datetime(2026, 9, 26, 14, 0),
        estimated_cost=Decimal("250"),
        position=1,
    )
    item3 = PlanItem(
        plan_id=plan_id,
        name="Kirstenbosch Garden",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 14, 30),
        end_time=datetime(2026, 9, 26, 16, 30),
        estimated_cost=Decimal("220"),
        position=2,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Full day out",
        context=PlanningContext(plan_id=plan_id, start_time=datetime(2026, 9, 26, 11, 0)),
        items=[item1, item2, item3],
    )
    mock_planning_service.get_plan.return_value = plan
    mock_decision_service.recommend.return_value = DecisionResult(candidates=(), source="fixture", is_live=False, attribution=None, freshness="fixture")

    service = PlanAdaptationService(mock_planning_service, mock_decision_service, mock_info_service)
    adaptation = await service.propose_adaptation(user_id, plan_id, "I only have one hour")

    assert ChangeType.DURATION_LIMIT_CHANGED in adaptation.changes_detected
    # Scaled down to 1 stop instead of squeezing 3 stops impossibly
    assert len(adaptation.adapted_items) == 1
    assert adaptation.diffs[0].action in (ItemAction.KEPT, ItemAction.RESCHEDULED)
    # Remaining 2 stops are marked REMOVED with reasons
    assert adaptation.diffs[1].action is ItemAction.REMOVED
    assert adaptation.diffs[2].action is ItemAction.REMOVED
    assert adaptation.is_feasible is True
    assert adaptation.feasibility_note is not None
