"""Milestone 5 Scenario Verification Tests.

Verifies Scenarios A through G against the complete adaptive planning pipeline:
- Scenario A: Later Start (11:00 -> 14:00)
- Scenario B: Budget Reduction (R1000 -> R600)
- Scenario C: Group Size (2 -> 4)
- Scenario D: Exclusion (nothing outdoors)
- Scenario E: Venue Closed / Invalidated
- Scenario F: Location Change (City Bowl -> Camps Bay)
- Scenario G: Impossible Change / 1-hour window (scales down cleanly)
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.information import PlanningInformationService
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.adaptation import ChangeType, ItemAction, PlanAdaptation
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
from app.domain.entities.planning.plan import Plan
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


class InMemoryPlanRepository:
    def __init__(self) -> None:
        self._plans: dict[tuple[object, object], Plan] = {}

    async def create(self, plan: Plan) -> Plan:
        self._plans[(plan.id, plan.user_id)] = plan
        return plan

    async def update(self, plan: Plan) -> Plan:
        self._plans[(plan.id, plan.user_id)] = plan
        return plan

    async def get(self, plan_id: object, user_id: object) -> Plan | None:
        return self._plans.get((plan_id, user_id))

    async def create_item(self, user_id: object, plan_id: object, item: PlanItem) -> PlanItem:
        plan = self._plans.get((plan_id, user_id))
        if plan:
            plan.items.append(item)
        return item

    async def delete_item(self, user_id: object, plan_id: object, item_id: object) -> bool:
        plan = self._plans.get((plan_id, user_id))
        if plan:
            plan.items = [i for i in plan.items if i.id != item_id]
            return True
        return False

    async def list_items(self, user_id: object, plan_id: object) -> list[PlanItem]:
        plan = self._plans.get((plan_id, user_id))
        return list(plan.items) if plan else []


@pytest.fixture
def plan_repo() -> InMemoryPlanRepository:
    return InMemoryPlanRepository()


@pytest.fixture
def planning_service(plan_repo: InMemoryPlanRepository) -> PlanningService:
    return PlanningService(plan_repo)


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


@pytest.mark.asyncio
async def test_scenario_a_later_start(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario A: 'Actually we can only leave at 2' shifts times, keeps valid venues, reschedules sequence."""
    user_id = uuid4()
    plan_id = uuid4()

    item1 = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 15),
        estimated_cost=Decimal("140"),
        location="36 Buitenkant St, Cape Town",
        position=0,
    )
    item2 = PlanItem(
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 45),
        end_time=datetime(2026, 9, 26, 14, 45),
        estimated_cost=Decimal("250"),
        location="Silo District, V&A Waterfront",
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Date around 11 until 7, R800",
        context=PlanningContext(
            plan_id=plan_id,
            location="Cape Town",
            start_time=datetime(2026, 9, 26, 11, 0),
            end_time=datetime(2026, 9, 26, 19, 0),
            group_size=2,
        ),
        constraints=[
            Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="R800", numeric_value=Decimal("800")),
            Constraint(plan_id=plan_id, type=ConstraintType.REQUIREMENT, value="start_time:11:00"),
            Constraint(plan_id=plan_id, type=ConstraintType.REQUIREMENT, value="end_time:19:00"),
        ],
        items=[item1, item2],
    )
    await planning_service._repository.create(plan)
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "Actually we can only leave at 2")

    assert ChangeType.TIME_SHIFT in adaptation.changes_detected
    assert len(adaptation.adapted_items) == 2
    # Start time is moved to 14:00
    assert adaptation.adapted_items[0].start_time.hour == 14
    assert adaptation.adapted_items[0].start_time.minute == 0
    # Minimal change: both venues preserved, marked RESCHEDULED
    assert adaptation.diffs[0].action is ItemAction.RESCHEDULED
    assert adaptation.diffs[0].original_name == "Truth Coffee Roasting"
    assert adaptation.diffs[1].action is ItemAction.RESCHEDULED
    assert adaptation.diffs[1].original_name == "Zeitz MOCAA"


@pytest.mark.asyncio
async def test_scenario_b_budget_reduction(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario B: 'Actually keep it under R600' replaces expensive items, preserves affordable ones."""
    user_id = uuid4()
    plan_id = uuid4()

    item_affordable = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 15),
        estimated_cost=Decimal("120"),
        position=0,
    )
    item_expensive = PlanItem(
        plan_id=plan_id,
        name="Fine Dining Experience",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 13, 0),
        end_time=datetime(2026, 9, 26, 15, 0),
        estimated_cost=Decimal("850"),
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Saturday day out",
        context=PlanningContext(plan_id=plan_id, location="Cape Town"),
        constraints=[
            Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="R1000", numeric_value=Decimal("1000")),
        ],
        items=[item_affordable, item_expensive],
    )
    await planning_service._repository.create(plan)

    # Cheaper candidate to replace the expensive one
    cheaper_cand = DecisionCandidate(
        option_id=uuid4(),
        option_type=CandidateType.PLACE,
        name="Honest Chocolate Café",
        is_eligible=True,
        score=95,
        reasons=(
            DecisionReason(
                type=ReasonType.PREFERENCE,
                outcome=ReasonOutcome.SUPPORTED,
                message="Affordable artisanal cafe",
            ),
        ),
        category=InformationCategory.FOOD,
        cost=Decimal("180"),
        duration_minutes=60,
        location="64A Wale St, Cape Town",
    )
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(cheaper_cand,), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "Actually keep it under R600")

    assert ChangeType.BUDGET_REDUCED in adaptation.changes_detected
    assert adaptation.new_total_cost <= Decimal("600")
    # Affordable item kept
    assert any(d.original_name == "Truth Coffee Roasting" for d in adaptation.diffs)
    # Expensive item replaced with affordable candidate
    replaced_diff = next(d for d in adaptation.diffs if d.original_name == "Fine Dining Experience")
    assert replaced_diff.action is ItemAction.REPLACED
    assert replaced_diff.new_name == "Honest Chocolate Café"


@pytest.mark.asyncio
async def test_scenario_c_group_size_increase(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario C: 'Actually two more friends are coming' updates group size to 4."""
    user_id = uuid4()
    plan_id = uuid4()

    item_cafe = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        estimated_cost=Decimal("140"),
        position=0,
    )
    item_intimate = PlanItem(
        plan_id=plan_id,
        name="Tiny Intimate Bistro",
        item_type=PlanItemType.FOOD,
        description="A romantic corner with couples table",
        estimated_cost=Decimal("260"),
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Date for two",
        context=PlanningContext(plan_id=plan_id, group_size=2),
        constraints=[
            Constraint(plan_id=plan_id, type=ConstraintType.GROUP_SIZE, value="2", numeric_value=Decimal("2")),
        ],
        items=[item_cafe, item_intimate],
    )
    await planning_service._repository.create(plan)

    group_venue = DecisionCandidate(
        option_id=uuid4(),
        option_type=CandidateType.PLACE,
        name="Grand Africa Café & Beach",
        is_eligible=True,
        score=90,
        reasons=(
            DecisionReason(
                type=ReasonType.PREFERENCE,
                outcome=ReasonOutcome.SUPPORTED,
                message="Spacious venue suited for groups",
            ),
        ),
        category=InformationCategory.FOOD,
        cost=Decimal("280"),
        duration_minutes=90,
        location="Granger Bay, Cape Town",
    )
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(group_venue,), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "Actually two more friends are coming")

    assert ChangeType.GROUP_SIZE_CHANGED in adaptation.changes_detected
    # Tiny intimate bistro replaced
    bistro_diff = next(d for d in adaptation.diffs if d.original_name == "Tiny Intimate Bistro")
    assert bistro_diff.action is ItemAction.REPLACED
    assert bistro_diff.new_name == "Grand Africa Café & Beach"


@pytest.mark.asyncio
async def test_scenario_d_exclusion_nothing_outdoors(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario D: 'Actually nothing outdoors' replaces outdoor items and preserves indoor ones."""
    user_id = uuid4()
    plan_id = uuid4()

    item_food = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 15),
        estimated_cost=Decimal("130"),
        position=0,
    )
    item_outdoor = PlanItem(
        plan_id=plan_id,
        name="Kirstenbosch National Botanical Garden",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 45),
        end_time=datetime(2026, 9, 26, 15, 0),
        estimated_cost=Decimal("220"),
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Date in Cape Town",
        context=PlanningContext(plan_id=plan_id, location="Cape Town"),
        items=[item_food, item_outdoor],
    )
    await planning_service._repository.create(plan)

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
                message="Indoor cultural exhibition",
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

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "Actually nothing outdoors")

    assert ChangeType.EXCLUSION_ADDED in adaptation.changes_detected
    outdoor_diff = next(d for d in adaptation.diffs if d.original_name == "Kirstenbosch National Botanical Garden")
    assert outdoor_diff.action is ItemAction.REPLACED
    assert outdoor_diff.new_name == "Iziko South African Museum"
    # Truth Coffee kept
    coffee_diff = next(d for d in adaptation.diffs if d.original_name == "Truth Coffee")
    assert coffee_diff.action in (ItemAction.KEPT, ItemAction.RESCHEDULED)


@pytest.mark.asyncio
async def test_scenario_e_closed_venue(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario E: 'Truth Coffee is closed' replaces Truth Coffee and keeps all other stops intact."""
    user_id = uuid4()
    plan_id = uuid4()

    item1 = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 15),
        estimated_cost=Decimal("140"),
        position=0,
    )
    item2 = PlanItem(
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 45),
        end_time=datetime(2026, 9, 26, 14, 45),
        estimated_cost=Decimal("250"),
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Saturday day out",
        items=[item1, item2],
    )
    await planning_service._repository.create(plan)

    replacement_cafe = DecisionCandidate(
        option_id=uuid4(),
        option_type=CandidateType.PLACE,
        name="Honest Chocolate Café",
        is_eligible=True,
        score=95,
        reasons=(
            DecisionReason(
                type=ReasonType.PREFERENCE,
                outcome=ReasonOutcome.SUPPORTED,
                message="Open coffee spot",
            ),
        ),
        category=InformationCategory.FOOD,
        cost=Decimal("130"),
        duration_minutes=60,
        location="Wale St, Cape Town",
    )
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(replacement_cafe,), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "Truth Coffee is closed")

    assert ChangeType.VENUE_INVALIDATED in adaptation.changes_detected
    # Truth Coffee replaced
    coffee_diff = next(d for d in adaptation.diffs if d.original_name == "Truth Coffee Roasting")
    assert coffee_diff.action is ItemAction.REPLACED
    assert coffee_diff.new_name == "Honest Chocolate Café"
    # Zeitz MOCAA strictly preserved
    museum_diff = next(d for d in adaptation.diffs if d.original_name == "Zeitz MOCAA")
    assert museum_diff.action in (ItemAction.KEPT, ItemAction.RESCHEDULED)


@pytest.mark.asyncio
async def test_scenario_f_location_change(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario F: 'Actually let's do Camps Bay' shifts location and substitutes out-of-area venues."""
    user_id = uuid4()
    plan_id = uuid4()

    item_city = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        location="36 Buitenkant St, City Bowl",
        estimated_cost=Decimal("140"),
        position=0,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Saturday day out",
        context=PlanningContext(plan_id=plan_id, location="City Bowl"),
        items=[item_city],
    )
    await planning_service._repository.create(plan)

    camps_bay_cafe = DecisionCandidate(
        option_id=uuid4(),
        option_type=CandidateType.PLACE,
        name="The Bungalow Camps Bay",
        is_eligible=True,
        score=98,
        reasons=(
            DecisionReason(
                type=ReasonType.PREFERENCE,
                outcome=ReasonOutcome.SUPPORTED,
                message="Located in Camps Bay",
            ),
        ),
        category=InformationCategory.FOOD,
        cost=Decimal("250"),
        duration_minutes=90,
        location="Victoria Rd, Camps Bay",
        address="Victoria Rd, Camps Bay",
    )
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(camps_bay_cafe,), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "Actually let's do Camps Bay")

    assert ChangeType.LOCATION_CHANGED in adaptation.changes_detected
    assert len(adaptation.adapted_items) == 1
    assert "Camps Bay" in adaptation.adapted_items[0].location
    assert adaptation.diffs[0].action is ItemAction.REPLACED
    assert adaptation.diffs[0].new_name == "The Bungalow Camps Bay"


@pytest.mark.asyncio
async def test_scenario_g_impossible_window_scales_down_without_fabrication(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Scenario G: 'I only have one hour' scales down to 1 stop instead of squeezing 3 stops impossibly."""
    user_id = uuid4()
    plan_id = uuid4()

    item1 = PlanItem(
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 11, 0),
        end_time=datetime(2026, 9, 26, 12, 0),
        position=0,
    )
    item2 = PlanItem(
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 12, 30),
        end_time=datetime(2026, 9, 26, 14, 30),
        position=1,
    )
    item3 = PlanItem(
        plan_id=plan_id,
        name="Kirstenbosch Garden",
        item_type=PlanItemType.ACTIVITY,
        start_time=datetime(2026, 9, 26, 15, 0),
        end_time=datetime(2026, 9, 26, 17, 0),
        position=2,
    )

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Full day itinerary",
        context=PlanningContext(plan_id=plan_id, start_time=datetime(2026, 9, 26, 11, 0)),
        items=[item1, item2, item3],
    )
    await planning_service._repository.create(plan)
    mock_decision_service.recommend.return_value = DecisionResult(
        candidates=(), source="fixture", is_live=False, attribution=None, freshness="fixture"
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    adaptation = await adaptation_service.propose_adaptation(user_id, plan_id, "I only have one hour")

    assert ChangeType.DURATION_LIMIT_CHANGED in adaptation.changes_detected
    # Scaled down to 1 stop: no overlapping or fabricated 15-minute stops!
    assert len(adaptation.adapted_items) == 1
    assert adaptation.adapted_items[0].name == "Truth Coffee Roasting"
    # Remaining 2 stops removed with explicit reason
    assert adaptation.diffs[1].action is ItemAction.REMOVED
    assert adaptation.diffs[2].action is ItemAction.REMOVED
    assert adaptation.is_feasible is True
    assert "scaled down" in adaptation.feasibility_note.lower()


@pytest.mark.asyncio
async def test_apply_adaptation_commits_to_repository(
    planning_service: PlanningService,
    mock_decision_service: MagicMock,
    mock_info_service: MagicMock,
) -> None:
    """Verifies that apply_adaptation commits the proposed changes into the database."""
    user_id = uuid4()
    plan_id = uuid4()

    item1 = PlanItem(
        plan_id=plan_id,
        name="Old Item",
        item_type=PlanItemType.FOOD,
        position=0,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Original Plan",
        items=[item1],
    )
    await planning_service._repository.create(plan)

    new_item = PlanItem(
        plan_id=plan_id,
        name="Adapted Item",
        item_type=PlanItemType.FOOD,
        start_time=datetime(2026, 9, 26, 14, 0),
        end_time=datetime(2026, 9, 26, 15, 0),
        estimated_cost=Decimal("200"),
        position=0,
    )
    adaptation = PlanAdaptation(
        plan_id=plan_id,
        changes_detected=[ChangeType.TIME_SHIFT],
        narrative_summary="Adapted to 14:00",
        diffs=[],
        adapted_items=[new_item],
        new_start_time=datetime(2026, 9, 26, 14, 0),
        new_end_time=datetime(2026, 9, 26, 15, 0),
        new_total_cost=Decimal("200"),
    )

    adaptation_service = PlanAdaptationService(planning_service, mock_decision_service, mock_info_service)
    updated_plan = await adaptation_service.apply_adaptation(user_id, plan_id, adaptation)

    persisted = await planning_service.get_plan(user_id, plan_id)
    assert len(persisted.items) == 1
    assert persisted.items[0].name == "Adapted Item"
    assert persisted.items[0].start_time.hour == 14
