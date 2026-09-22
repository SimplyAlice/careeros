from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.planning.dtos import PlanningIntent
from app.application.planning.errors import PlanningNotFoundError
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.constraint import ConstraintType
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


class FakePlanRepository:
    def __init__(self) -> None:
        self.created_plan: Plan | None = None
        self._plans: dict[tuple[object, object], Plan] = {}
        self._items: dict[tuple[object, object, object], PlanItem] = {}

    async def create(self, plan: Plan) -> Plan:
        self.created_plan = plan
        self._plans[(plan.id, plan.user_id)] = plan
        return plan

    async def get(self, plan_id: object, user_id: object) -> Plan | None:
        return self._plans.get((plan_id, user_id))

    async def delete(self, plan_id: object, user_id: object) -> bool:
        if (plan_id, user_id) in self._plans:
            del self._plans[(plan_id, user_id)]
            return True
        return False

    async def create_item(self, user_id: object, plan_id: object, item: PlanItem) -> PlanItem | None:
        plan = await self.get(plan_id, user_id)
        if plan is None:
            return None
        self._items[(item.id, plan_id, user_id)] = item
        plan.items.append(item)
        return item

    async def get_item(self, user_id: object, plan_id: object, item_id: object) -> PlanItem | None:
        return self._items.get((item_id, plan_id, user_id))

    async def delete_item(self, user_id: object, plan_id: object, item_id: object) -> bool:
        if (item_id, plan_id, user_id) in self._items:
            del self._items[(item_id, plan_id, user_id)]
            plan = await self.get(plan_id, user_id)
            if plan is not None:
                plan.items = [it for it in plan.items if it.id != item_id]
            return True
        return False


@pytest.mark.asyncio
async def test_create_plan_from_intent_builds_structured_plan_data() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)

    user_id = uuid4()
    intent = PlanningIntent(
        user_id=user_id,
        raw_request="I want a fun Saturday with 3 friends, R800 total, somewhere in Cape Town.",
        goal="I want a fun Saturday with 3 friends, R800 total, somewhere in Cape Town.",
        location="Cape Town",
        group_size=4,
        budget_max=Decimal("800"),
    )

    await service.create_plan_from_intent(intent)

    assert repository.created_plan is not None
    assert repository.created_plan.user_id == user_id
    assert repository.created_plan.intention == intent.raw_request
    assert repository.created_plan.context is not None
    assert repository.created_plan.context.location == "Cape Town"
    assert repository.created_plan.context.group_size == 4

    assert len(repository.created_plan.constraints) == 1

    budget = repository.created_plan.constraints[0]
    assert budget.type == ConstraintType.BUDGET_MAX
    assert budget.value == "R800"
    assert budget.numeric_value == Decimal("800")


@pytest.mark.asyncio
async def test_delete_archived_plan_is_rejected() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()
    plan = Plan(user_id=user_id, intention="Archived plan", status=PlanStatus.ARCHIVED)
    await repository.create(plan)

    with pytest.raises(ValueError, match="Archived plans cannot be modified."):
        await service.delete_plan(user_id, plan.id)

    # Verify plan was not deleted from repository
    assert await repository.get(plan.id, user_id) is not None


@pytest.mark.asyncio
async def test_delete_item_from_archived_plan_is_rejected() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()
    plan = Plan(user_id=user_id, intention="Archived plan with item", status=PlanStatus.DRAFT)
    await repository.create(plan)
    item = PlanItem(plan_id=plan.id, name="Test item", item_type=PlanItemType.ACTIVITY)
    await repository.create_item(user_id, plan.id, item)

    # Archive the plan
    plan.status = PlanStatus.ARCHIVED

    with pytest.raises(ValueError, match="Archived plans cannot be modified."):
        await service.delete_item(user_id, plan.id, item.id)

    # Verify item was not deleted
    assert await repository.get_item(user_id, plan.id, item.id) is not None


@pytest.mark.asyncio
async def test_delete_mutable_plan_and_item_succeeds() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()
    plan = Plan(user_id=user_id, intention="Mutable plan", status=PlanStatus.DRAFT)
    await repository.create(plan)
    item = PlanItem(plan_id=plan.id, name="Deletable item", item_type=PlanItemType.ACTIVITY)
    await repository.create_item(user_id, plan.id, item)

    await service.delete_item(user_id, plan.id, item.id)
    assert await repository.get_item(user_id, plan.id, item.id) is None

    await service.delete_plan(user_id, plan.id)
    assert await repository.get(plan.id, user_id) is None


@pytest.mark.asyncio
async def test_delete_plan_and_item_enforce_ownership() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)
    owner_id = uuid4()
    other_user_id = uuid4()
    plan = Plan(user_id=owner_id, intention="Owner plan", status=PlanStatus.DRAFT)
    await repository.create(plan)
    item = PlanItem(plan_id=plan.id, name="Owner item", item_type=PlanItemType.ACTIVITY)
    await repository.create_item(owner_id, plan.id, item)

    # Other user cannot delete owner's item
    with pytest.raises(PlanningNotFoundError):
        await service.delete_item(other_user_id, plan.id, item.id)

    # Other user cannot delete owner's plan
    with pytest.raises(PlanningNotFoundError):
        await service.delete_plan(other_user_id, plan.id)
