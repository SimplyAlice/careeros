from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.planning.dtos import PlanningIntent
from app.application.planning.errors import PlanningNotFoundError
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.constraint import ConstraintType
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType
from app.domain.entities.planning.understanding import PlanningUnderstanding


class FakePlanRepository:
    def __init__(self) -> None:
        self.created_plan: Plan | None = None
        self._plans: dict[tuple[object, object], Plan] = {}
        self._items: dict[tuple[object, object, object], PlanItem] = {}

    async def create(self, plan: Plan) -> Plan:
        self.created_plan = plan
        self._plans[(plan.id, plan.user_id)] = plan
        return plan

    async def update(self, plan: Plan) -> Plan:
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


@pytest.mark.asyncio
async def test_create_plan_from_understanding_builds_rich_constraints() -> None:
    from app.domain.entities.planning.understanding import BudgetKind, PlanningUnderstanding
    from app.domain.entities.planning.information import InformationCategory

    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()

    understanding = PlanningUnderstanding(
        raw_request="Date night with my boyfriend, R800, nothing too fancy",
        goal="Plan a date with boyfriend",
        occasion="date",
        people_count=2,
        relationship_context="boyfriend",
        date_spec="Saturday",
        location="Cape Town",
        budget_amount=Decimal("800"),
        budget_kind=BudgetKind.APPROXIMATE,
        preferences=("nice",),
        exclusions=("not_too_fancy",),
        activity_types=(InformationCategory.FOOD,),
    )

    plan = await service.create_plan_from_understanding(user_id, understanding)

    assert plan.user_id == user_id
    assert plan.context is not None
    assert plan.context.group_size == 2
    assert plan.context.location == "Cape Town"
    assert "Date with Boyfriend" in plan.title

    constraint_vals = {c.value for c in plan.constraints}
    assert "occasion:date" in constraint_vals
    assert "exclude:not_too_fancy" in constraint_vals
    assert "R800" in constraint_vals
    assert "date:Saturday" in constraint_vals


@pytest.mark.asyncio
async def test_modify_plan_cheaper_and_exclusions() -> None:
    from app.domain.entities.planning.understanding import BudgetKind, PlanningUnderstanding

    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()

    understanding = PlanningUnderstanding(
        raw_request="Saturday afternoon",
        goal="Plan an afternoon",
        budget_amount=Decimal("1000"),
        budget_kind=BudgetKind.HARD_MAX,
        people_count=2,
    )
    plan = await service.create_plan_from_understanding(user_id, understanding)

    # 1. Tweak: make it cheaper
    modified_plan = await service.modify_plan(user_id, plan.id, "Make it cheaper please")
    budget_constraint = next(c for c in modified_plan.constraints if c.type is ConstraintType.BUDGET_MAX)
    assert budget_constraint.numeric_value == Decimal("700")  # 1000 * 0.70

    # 2. Tweak: no outdoors and add 2 people
    modified_plan_2 = await service.modify_plan(user_id, plan.id, "No outdoors, and add 2 people")
    assert modified_plan_2.context.group_size == 4
    assert any(c.value == "exclude:no_outdoors" for c in modified_plan_2.constraints)


@pytest.mark.asyncio
async def test_create_plan_temporal_persistence() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()

    understanding = PlanningUnderstanding(
        raw_request="Saturday around 11 until 7 budget R800",
        goal="Plan Saturday",
        date_spec="Saturday",
        start_time="11:00",
        end_time="19:00",
        duration_limit_minutes=None,
    )
    plan = await service.create_plan_from_understanding(user_id, understanding)
    assert plan.context is not None
    assert plan.context.start_time is not None
    assert plan.context.start_time.hour == 11
    assert plan.context.end_time is not None
    assert plan.context.end_time.hour == 19

    c_vals = {c.value for c in plan.constraints}
    assert "start_time:11:00" in c_vals
    assert "end_time:19:00" in c_vals
    assert "date:Saturday" in c_vals


@pytest.mark.asyncio
async def test_modify_plan_temporal_adjustments() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()

    understanding = PlanningUnderstanding(
        raw_request="Saturday at 11 until 7",
        goal="Plan Saturday",
        date_spec="Saturday",
        start_time="11:00",
        end_time="19:00",
    )
    plan = await service.create_plan_from_understanding(user_id, understanding)

    # 1. Modify: start later
    mod1 = await service.modify_plan(user_id, plan.id, "Make it start later")
    c_vals1 = {c.value for c in mod1.constraints}
    assert "start_time:13:00" in c_vals1
    assert mod1.context.start_time.hour == 13

    # 2. Modify: home by 6
    mod2 = await service.modify_plan(user_id, plan.id, "I need to be home by 6")
    c_vals2 = {c.value for c in mod2.constraints}
    assert "end_time:18:00" in c_vals2
    assert mod2.context.end_time.hour == 18

    # 3. Modify: only have 3 hours
    mod3 = await service.modify_plan(user_id, plan.id, "We only have three hours")
    dur_c = next(c for c in mod3.constraints if c.type is ConstraintType.TIME_MAX)
    assert dur_c.numeric_value == Decimal("180")


@pytest.mark.asyncio
async def test_build_plan_understanding_read_temporal() -> None:
    from app.api.v1.planning.router import _build_plan_understanding_read, UnderstandingRead
    repository = FakePlanRepository()
    service = PlanningService(repository)
    user_id = uuid4()

    understanding = PlanningUnderstanding(
        raw_request="Saturday around 11 until 7 budget R800",
        goal="Plan Saturday",
        date_spec="Saturday",
        start_time="11:00",
        end_time="19:00",
        duration_limit_minutes=180,
    )
    plan = await service.create_plan_from_understanding(user_id, understanding)
    u_read = _build_plan_understanding_read(plan)

    assert isinstance(u_read, UnderstandingRead)
    assert u_read.start_time == "11:00"
    assert u_read.end_time == "19:00"
    assert u_read.duration_limit_minutes == 180
    assert u_read.date_spec == "Saturday"
