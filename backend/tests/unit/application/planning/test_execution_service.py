from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
import pytest

from app.application.planning.execution_service import PlanExecutionService
from app.application.planning.information import PlanningInformationService
from app.application.planning.planning_service import PlanningService
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


class FakePlanRepository:
    def __init__(self, plan: Plan | None = None) -> None:
        self.plans: dict[UUID, Plan] = {}
        if plan:
            self.plans[plan.id] = plan

    async def get(self, plan_id: UUID, user_id: UUID) -> Plan | None:
        p = self.plans.get(plan_id)
        if p and p.user_id == user_id:
            return p
        return None

    async def get_item(self, user_id: UUID, plan_id: UUID, item_id: UUID) -> PlanItem | None:
        plan = await self.get(plan_id, user_id)
        if not plan:
            return None
        return next((i for i in plan.items if i.id == item_id), None)

    async def update(self, plan: Plan) -> Plan:
        self.plans[plan.id] = plan
        return plan

    async def update_item(self, user_id: UUID, plan_id: UUID, item: PlanItem) -> PlanItem | None:
        plan = await self.get(plan_id, user_id)
        if not plan:
            return None
        for idx, existing in enumerate(plan.items):
            if existing.id == item.id:
                plan.items[idx] = item
                return item
        return None


class FakeInformationProvider:
    async def describe_source(self) -> InformationSource:
        return InformationSource(data_source="test_fixture", is_live=False)

    async def find_places(self, criteria) -> list[Place]:
        return []

    async def find_activities(self, criteria) -> list[Activity]:
        return []

    async def get_place(self, place_id: UUID) -> Place | None:
        return None

    async def get_activity(self, activity_id: UUID) -> Activity | None:
        return None


@pytest.fixture
def test_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def fake_plan(test_user_id: UUID) -> Plan:
    plan_id = uuid4()
    now = datetime(2026, 9, 26, 11, 0, tzinfo=UTC)

    # Item 1: Kloof Street House (has website, address, phone, reservation_url, times)
    item1 = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Kloof Street House",
        item_type=PlanItemType.FOOD,
        start_time=now,
        end_time=now + timedelta(minutes=90),
        estimated_cost=Decimal("200"),
        location="30 Kloof St, Gardens, Cape Town",
        position=0,
    )

    # Item 2: Sea Point Promenade (has website and address, but NO phone, NO reservation_url)
    item2 = PlanItem(
        id=uuid4(),
        plan_id=plan_id,
        name="Sea Point Promenade",
        item_type=PlanItemType.ACTIVITY,
        start_time=now + timedelta(minutes=90),
        end_time=now + timedelta(minutes=150),
        estimated_cost=Decimal("0"),
        location="Beach Rd, Sea Point, Cape Town",
        position=1,
    )

    plan = Plan(
        id=plan_id,
        user_id=test_user_id,
        intention="Date in Cape Town",
        title="Cape Town Outing",
        status=PlanStatus.READY,
        items=[item1, item2],
    )
    return plan


@pytest.fixture
def execution_service(fake_plan: Plan) -> PlanExecutionService:
    repo = FakePlanRepository(fake_plan)
    planning_service = PlanningService(repo)
    info_service = PlanningInformationService(FakeInformationProvider())
    return PlanExecutionService(planning_service, info_service)


@pytest.mark.asyncio
async def test_get_plan_actions_derives_truthful_actions(
    execution_service: PlanExecutionService, fake_plan: Plan, test_user_id: UUID
) -> None:
    plan_actions = await execution_service.get_plan_actions(test_user_id, fake_plan.id)
    assert plan_actions.plan_id == fake_plan.id
    assert plan_actions.plan_status == PlanExecutionStatus.READY.value
    assert len(plan_actions.items) == 2

    # Check Kloof Street House actions
    kloof_item = plan_actions.items[0]
    action_types = [a.action_type for a in kloof_item.actions]
    assert ExecutionActionType.OPEN_WEBSITE in action_types
    assert ExecutionActionType.DIRECTIONS in action_types
    assert ExecutionActionType.CALL in action_types
    assert ExecutionActionType.RESERVE in action_types
    assert ExecutionActionType.ADD_TO_CALENDAR in action_types
    assert ExecutionActionType.MARK_COMPLETE in action_types

    reserve_action = next(a for a in kloof_item.actions if a.action_type is ExecutionActionType.RESERVE)
    assert "kloofstreethouse.co.za/reservations" in (reserve_action.target_url or "")

    # Check Sea Point Promenade actions (NO CALL, NO RESERVE)
    sea_point_item = plan_actions.items[1]
    sea_point_types = [a.action_type for a in sea_point_item.actions]
    assert ExecutionActionType.OPEN_WEBSITE in sea_point_types
    assert ExecutionActionType.DIRECTIONS in sea_point_types
    assert ExecutionActionType.ADD_TO_CALENDAR in sea_point_types
    assert ExecutionActionType.MARK_COMPLETE in sea_point_types
    assert ExecutionActionType.CALL not in sea_point_types  # No phone number in catalog
    assert ExecutionActionType.RESERVE not in sea_point_types  # No reservation portal in catalog


@pytest.mark.asyncio
async def test_execute_website_action(
    execution_service: PlanExecutionService, fake_plan: Plan, test_user_id: UUID
) -> None:
    item_id = fake_plan.items[0].id
    result = await execution_service.execute_action(
        test_user_id, fake_plan.id, item_id, ExecutionActionType.OPEN_WEBSITE
    )
    assert result.status is ExecutionActionStatus.COMPLETED
    assert "kloofstreethouse.co.za" in (result.target_url or "")
    assert "Official website opened" in result.message


@pytest.mark.asyncio
async def test_execute_reserve_action_is_honest(
    execution_service: PlanExecutionService, fake_plan: Plan, test_user_id: UUID
) -> None:
    item_id = fake_plan.items[0].id
    result = await execution_service.execute_action(
        test_user_id, fake_plan.id, item_id, ExecutionActionType.RESERVE
    )
    # Status is IN_PROGRESS (not completed/confirmed) because user must finish on external portal
    assert result.status is ExecutionActionStatus.IN_PROGRESS
    assert "reservations" in (result.target_url or "")
    assert "Reservation page opened" in result.message
    assert "Reservation confirmed" not in result.message  # Never falsely claims confirmation!


@pytest.mark.asyncio
async def test_execute_unsupported_action_fails_honestly(
    execution_service: PlanExecutionService, fake_plan: Plan, test_user_id: UUID
) -> None:
    # Sea Point Promenade has no reservation URL
    sea_point_id = fake_plan.items[1].id
    result = await execution_service.execute_action(
        test_user_id, fake_plan.id, sea_point_id, ExecutionActionType.RESERVE
    )
    assert result.status is ExecutionActionStatus.UNAVAILABLE
    assert "not available" in result.message
    assert "plan is unchanged" in result.message


@pytest.mark.asyncio
async def test_unsafe_url_is_blocked(
    execution_service: PlanExecutionService, fake_plan: Plan, test_user_id: UUID
) -> None:
    item_id = fake_plan.items[0].id
    result = await execution_service.execute_action(
        test_user_id,
        fake_plan.id,
        item_id,
        ExecutionActionType.OPEN_WEBSITE,
        target_url="javascript:alert(1)",
    )
    assert result.status is ExecutionActionStatus.FAILED
    assert "security validation" in result.message


@pytest.mark.asyncio
async def test_complete_and_uncomplete_item_progression(
    execution_service: PlanExecutionService, fake_plan: Plan, test_user_id: UUID
) -> None:
    item1_id = fake_plan.items[0].id
    item2_id = fake_plan.items[1].id

    # 1. Complete item 1 -> item completed, plan IN_PROGRESS
    res1 = await execution_service.execute_action(
        test_user_id, fake_plan.id, item1_id, ExecutionActionType.MARK_COMPLETE
    )
    assert res1.item_status == PlanItemStatus.COMPLETED.value
    assert res1.plan_status == PlanExecutionStatus.IN_PROGRESS.value

    # Check via get_plan_actions
    actions_mid = await execution_service.get_plan_actions(test_user_id, fake_plan.id)
    assert actions_mid.plan_status == PlanExecutionStatus.IN_PROGRESS.value
    assert actions_mid.items[0].item_status == PlanItemStatus.COMPLETED.value
    assert actions_mid.items[1].item_status == PlanItemStatus.PLANNED.value

    # 2. Complete item 2 -> both completed, plan COMPLETED
    res2 = await execution_service.execute_action(
        test_user_id, fake_plan.id, item2_id, ExecutionActionType.MARK_COMPLETE
    )
    assert res2.item_status == PlanItemStatus.COMPLETED.value
    assert res2.plan_status == PlanExecutionStatus.COMPLETED.value

    # 3. Uncomplete item 1 -> item 1 PLANNED, plan IN_PROGRESS
    uncompleted = await execution_service.uncomplete_item(test_user_id, fake_plan.id, item1_id)
    assert uncompleted.status == PlanItemStatus.PLANNED

    actions_after = await execution_service.get_plan_actions(test_user_id, fake_plan.id)
    assert actions_after.plan_status == PlanExecutionStatus.IN_PROGRESS.value
