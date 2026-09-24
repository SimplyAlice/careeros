"""Milestone 6 Scenario Test Suite — Execution Layer.

Forensically verifies Scenarios A through H:
- Scenario A — Website (Verified official website without booking claims)
- Scenario B — Directions (Verified physical address via Google Maps)
- Scenario C — Phone (Call action appears only when phone number exists)
- Scenario D — Reservation URL (Reserve appears only with verified link; reports page opened, not confirmed)
- Scenario E — No Reservation (Venues without reservation links never show Reserve)
- Scenario F — Execution Failure (Safe error handling without mutating plan)
- Scenario G — Completion (Item completion progression without prematurely completing entire plan)
- Scenario H — Adaptation After Execution Problem (M5 re-evaluation generates new execution actions)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
import pytest

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.execution_service import PlanExecutionService
from app.application.planning.information import PlanningInformationService
from app.application.planning.intent_interpreter import IntentInterpreter
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.execution import (
    ExecutionActionStatus,
    ExecutionActionType,
    PlanExecutionStatus,
    PlanItemStatus,
)
from app.domain.entities.planning.information import (
    Activity,
    FreshnessKind,
    InformationCategory,
    InformationSource,
    Place,
)
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType
from app.infrastructure.planning.openstreetmap_provider import OpenStreetMapInformationProvider


class InMemoryPlanRepository:
    def __init__(self) -> None:
        self.plans: dict[UUID, Plan] = {}

    async def create(self, plan: Plan) -> Plan:
        self.plans[plan.id] = plan
        return plan

    async def get(self, plan_id: UUID, user_id: UUID) -> Plan | None:
        p = self.plans.get(plan_id)
        if p and p.user_id == user_id:
            return p
        return None

    async def update(self, plan: Plan) -> Plan:
        self.plans[plan.id] = plan
        return plan

    async def list_for_user(self, user_id: UUID) -> list[Plan]:
        return [p for p in self.plans.values() if p.user_id == user_id]

    async def create_item(self, user_id: UUID, plan_id: UUID, item: PlanItem) -> PlanItem | None:
        plan = await self.get(plan_id, user_id)
        if not plan:
            return None
        plan.items.append(item)
        return item

    async def get_item(self, user_id: UUID, plan_id: UUID, item_id: UUID) -> PlanItem | None:
        plan = await self.get(plan_id, user_id)
        if not plan:
            return None
        return next((i for i in plan.items if i.id == item_id), None)

    async def update_item(self, user_id: UUID, plan_id: UUID, item: PlanItem) -> PlanItem | None:
        plan = await self.get(plan_id, user_id)
        if not plan:
            return None
        for idx, existing in enumerate(plan.items):
            if existing.id == item.id:
                plan.items[idx] = item
                return item
        return None

    async def delete_item(self, user_id: UUID, plan_id: UUID, item_id: UUID) -> bool:
        plan = await self.get(plan_id, user_id)
        if not plan:
            return False
        plan.items = [i for i in plan.items if i.id != item_id]
        return True


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def plan_repo() -> InMemoryPlanRepository:
    return InMemoryPlanRepository()


@pytest.fixture
def osm_provider() -> OpenStreetMapInformationProvider:
    return OpenStreetMapInformationProvider(enable_network=False)


@pytest.fixture
def info_service(osm_provider: OpenStreetMapInformationProvider) -> PlanningInformationService:
    return PlanningInformationService(osm_provider)


@pytest.fixture
def decision_service(info_service: PlanningInformationService) -> PlanningDecisionService:
    return PlanningDecisionService(info_service)


@pytest.fixture
def planning_service(plan_repo: InMemoryPlanRepository) -> PlanningService:
    return PlanningService(plan_repo)


@pytest.fixture
def adaptation_service(
    planning_service: PlanningService,
    decision_service: PlanningDecisionService,
    info_service: PlanningInformationService,
) -> PlanAdaptationService:
    return PlanAdaptationService(planning_service, decision_service, info_service)


@pytest.fixture
def execution_service(
    planning_service: PlanningService, info_service: PlanningInformationService
) -> PlanExecutionService:
    return PlanExecutionService(planning_service, info_service)


# -----------------------------------------------------------------------------
# Scenario A — Website
# Create a plan containing a real venue with a verified official website.
# Expected: "Visit website" appears. Clicking it returns verified destination.
# OpsOS does not claim anything was booked.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_a_website(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Kirstenbosch National Botanical Garden",
        item_type=PlanItemType.ACTIVITY,
        location="Rhodes Dr, Newlands, Cape Town",
        position=0,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Visit gardens",
        status=PlanStatus.READY,
        items=[item],
    )
    await planning_service._repository.create(plan)

    actions_data = await execution_service.get_plan_actions(user_id, plan_id)
    kirstenbosch_actions = actions_data.items[0].actions

    website_action = next(
        (a for a in kirstenbosch_actions if a.action_type is ExecutionActionType.OPEN_WEBSITE),
        None,
    )
    assert website_action is not None
    assert website_action.label == "Visit website"
    assert "sanbi.org/gardens/kirstenbosch" in (website_action.target_url or "")

    result = await execution_service.execute_action(
        user_id, plan_id, item.id, ExecutionActionType.OPEN_WEBSITE
    )
    assert result.status is ExecutionActionStatus.COMPLETED
    assert "Official website opened" in result.message
    assert "booked" not in result.message.lower()


# -----------------------------------------------------------------------------
# Scenario B — Directions
# Create a plan containing a real physical venue.
# Expected: "Directions" appears using verified street address.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_b_directions(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Table Mountain Aerial Cableway",
        item_type=PlanItemType.ACTIVITY,
        location="Tafelberg Rd, Gardens, Cape Town",
        position=0,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Go up Table Mountain",
        status=PlanStatus.READY,
        items=[item],
    )
    await planning_service._repository.create(plan)

    actions_data = await execution_service.get_plan_actions(user_id, plan_id)
    table_mtn_actions = actions_data.items[0].actions

    directions_action = next(
        (a for a in table_mtn_actions if a.action_type is ExecutionActionType.DIRECTIONS),
        None,
    )
    assert directions_action is not None
    assert directions_action.label == "Get directions"
    assert "maps/search" in (directions_action.target_url or "")
    assert "Tafelberg" in (directions_action.target_url or "")

    result = await execution_service.execute_action(
        user_id, plan_id, item.id, ExecutionActionType.DIRECTIONS
    )
    assert result.status is ExecutionActionStatus.COMPLETED
    assert "Directions to 'Table Mountain Aerial Cableway' opened in Google Maps" in result.message


# -----------------------------------------------------------------------------
# Scenario C — Phone
# Real venue with verified phone number -> Call appears.
# Venue without phone number -> Call does NOT appear.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_c_phone(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    # Truth Coffee has phone (+27 21 200 0440)
    truth_item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        location="36 Buitenkant St, City Bowl, Cape Town",
        position=0,
    )
    # Sea Point Promenade has NO phone
    sea_point_item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Sea Point Promenade",
        item_type=PlanItemType.ACTIVITY,
        location="Beach Rd, Sea Point, Cape Town",
        position=1,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Coffee and coastal walk",
        status=PlanStatus.READY,
        items=[truth_item, sea_point_item],
    )
    await planning_service._repository.create(plan)

    actions_data = await execution_service.get_plan_actions(user_id, plan_id)

    # Truth Coffee has Call
    truth_actions = actions_data.items[0].actions
    truth_call = next((a for a in truth_actions if a.action_type is ExecutionActionType.CALL), None)
    assert truth_call is not None
    assert truth_call.target_url == "tel:+27212000440"

    # Sea Point Promenade has NO Call
    sea_point_actions = actions_data.items[1].actions
    sea_point_call = next((a for a in sea_point_actions if a.action_type is ExecutionActionType.CALL), None)
    assert sea_point_call is None


# -----------------------------------------------------------------------------
# Scenario D — Reservation URL
# Venue with verified external reservation destination.
# Expected: "Reserve" appears. Status is IN_PROGRESS ("Reservation page opened").
# NOT: "Reservation confirmed".
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_d_reservation_url(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Kloof Street House",
        item_type=PlanItemType.FOOD,
        location="30 Kloof St, Gardens, Cape Town",
        position=0,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Dinner date",
        status=PlanStatus.READY,
        items=[item],
    )
    await planning_service._repository.create(plan)

    actions_data = await execution_service.get_plan_actions(user_id, plan_id)
    actions = actions_data.items[0].actions

    reserve_action = next((a for a in actions if a.action_type is ExecutionActionType.RESERVE), None)
    assert reserve_action is not None
    assert reserve_action.target_url == "https://www.kloofstreethouse.co.za/reservations"

    result = await execution_service.execute_action(
        user_id, plan_id, item.id, ExecutionActionType.RESERVE
    )
    assert result.status is ExecutionActionStatus.IN_PROGRESS
    assert "Reservation page opened for 'Kloof Street House'" in result.message
    assert "Reservation confirmed" not in result.message


# -----------------------------------------------------------------------------
# Scenario E — No Reservation
# Venue with no verified reservation destination.
# Expected: "Reserve" does NOT appear.
# User still gets Website and Directions where supported.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_e_no_reservation(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Company's Garden",
        item_type=PlanItemType.ACTIVITY,
        location="15 Queen Victoria St, City Bowl, Cape Town",
        position=0,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Afternoon stroll",
        status=PlanStatus.READY,
        items=[item],
    )
    await planning_service._repository.create(plan)

    actions_data = await execution_service.get_plan_actions(user_id, plan_id)
    actions = actions_data.items[0].actions
    action_types = [a.action_type for a in actions]

    assert ExecutionActionType.RESERVE not in action_types
    assert ExecutionActionType.OPEN_WEBSITE in action_types
    assert ExecutionActionType.DIRECTIONS in action_types


# -----------------------------------------------------------------------------
# Scenario F — Execution Failure
# Break or invalidate an action destination (e.g. unsafe scheme).
# Expected: Clear failure message, plan remains intact, no false completion.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_f_execution_failure(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        location="36 Buitenkant St, City Bowl, Cape Town",
        position=0,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Morning coffee",
        status=PlanStatus.READY,
        items=[item],
    )
    await planning_service._repository.create(plan)

    # Invalidate action destination with unsafe scheme
    result = await execution_service.execute_action(
        user_id,
        plan_id,
        item.id,
        ExecutionActionType.OPEN_WEBSITE,
        target_url="javascript:malicious_code()",
    )
    assert result.status is ExecutionActionStatus.FAILED
    assert "security validation" in result.message
    assert "plan is unchanged" in result.message

    # Verify plan was not mutated
    unchanged_plan = await planning_service.get_plan(user_id, plan_id)
    assert unchanged_plan.items[0].status == PlanItemStatus.PLANNED
    assert unchanged_plan.status == PlanStatus.READY


# -----------------------------------------------------------------------------
# Scenario G — Completion
# Complete a supported plan item action.
# Expected: Item shows completed state, remaining items remain actionable,
# entire plan is not marked completed unless all items are complete.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_g_completion(
    planning_service: PlanningService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    item1 = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Truth Coffee Roasting",
        item_type=PlanItemType.FOOD,
        position=0,
    )
    item2 = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        position=1,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Coffee and art",
        status=PlanStatus.READY,
        items=[item1, item2],
    )
    await planning_service._repository.create(plan)

    # Complete item 1 only
    result1 = await execution_service.execute_action(
        user_id, plan_id, item1.id, ExecutionActionType.MARK_COMPLETE
    )
    assert result1.item_status == PlanItemStatus.COMPLETED.value
    # Plan is in progress, NOT completed
    assert result1.plan_status == PlanExecutionStatus.IN_PROGRESS.value

    # Verify item 2 is still PLANNED and actionable
    actions_data = await execution_service.get_plan_actions(user_id, plan_id)
    assert actions_data.plan_status == PlanExecutionStatus.IN_PROGRESS.value
    assert actions_data.items[0].item_status == PlanItemStatus.COMPLETED.value
    assert actions_data.items[1].item_status == PlanItemStatus.PLANNED.value
    assert len(actions_data.items[1].actions) > 0

    # Complete item 2 -> now entire plan is COMPLETED
    result2 = await execution_service.execute_action(
        user_id, plan_id, item2.id, ExecutionActionType.MARK_COMPLETE
    )
    assert result2.item_status == PlanItemStatus.COMPLETED.value
    assert result2.plan_status == PlanExecutionStatus.COMPLETED.value


# -----------------------------------------------------------------------------
# Scenario H — Adaptation After Execution Problem
# A venue becomes unusable (e.g. user reports "Kloof Street House is fully booked").
# Expected: M5 adaptation proposes replacement, user accepts, updated plan
# generates new execution actions for the replacement venue.
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_h_adaptation_after_execution_problem(
    planning_service: PlanningService,
    adaptation_service: PlanAdaptationService,
    execution_service: PlanExecutionService,
    user_id: UUID,
) -> None:
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)

    kloof_item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Kloof Street House",
        item_type=PlanItemType.FOOD,
        start_time=now,
        end_time=now + timedelta(minutes=90),
        estimated_cost=Decimal("170"),
        location="30 Kloof St, Gardens, Cape Town",
        position=0,
    )
    garden_item = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Company's Garden",
        item_type=PlanItemType.ACTIVITY,
        start_time=now + timedelta(minutes=90),
        end_time=now + timedelta(minutes=150),
        estimated_cost=Decimal("0"),
        location="15 Queen Victoria St, City Bowl, Cape Town",
        position=1,
    )
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        intention="Dinner and walk in Cape Town",
        status=PlanStatus.READY,
        context=PlanningContext(plan_id=plan_id, location="Cape Town", group_size=2),
        constraints=[Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="500", numeric_value=Decimal("500"))],
        items=[kloof_item, garden_item],
    )
    await planning_service._repository.create(plan)

    # 1. Verify initial execution action for Kloof Street House
    initial_actions = await execution_service.get_plan_actions(user_id, plan_id)
    assert initial_actions.items[0].item_name == "Kloof Street House"
    assert any(a.action_type is ExecutionActionType.RESERVE for a in initial_actions.items[0].actions)

    # 2. User encounters execution problem: "Kloof Street House is fully booked"
    adaptation_proposal = await adaptation_service.propose_adaptation(
        user_id, plan_id, "Kloof Street House is closed"
    )
    assert adaptation_proposal.is_feasible is True
    # Kloof Street House is replaced, Company's Garden is KEPT
    diff_actions = {d.action.value for d in adaptation_proposal.diffs}
    assert "replaced" in diff_actions

    # 3. User accepts adaptation
    updated_plan = await adaptation_service.apply_adaptation(
        user_id, plan_id, adaptation_proposal
    )

    # 4. Execution actions automatically update for the new replacement venue
    adapted_actions = await execution_service.get_plan_actions(user_id, plan_id)
    item_names = [i.item_name for i in adapted_actions.items]
    assert "Kloof Street House" not in item_names
    assert "Company's Garden" in item_names  # Preserved!
    # New actions generated for the replacement venue
    assert len(adapted_actions.items) >= 2
    assert len(adapted_actions.items[0].actions) > 0
