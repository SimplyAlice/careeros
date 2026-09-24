from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.planning.errors import OptionNotFoundError, PlanningNotFoundError
from app.application.planning.information import PlanningInformationService
from app.application.planning.planning_service import PlanningService
from app.application.planning.selection_service import PlanSelectionService, criteria_from_plan
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.decision import CandidateType
from app.domain.entities.planning.information import Activity, InformationCategory, InformationSource, Place
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType

PLACE_ID = UUID("10000000-0000-0000-0000-0000000000a1")
ACTIVITY_ID = UUID("20000000-0000-0000-0000-0000000000b1")


class FakeProvider:
    def __init__(self, places=(), activities=()) -> None:
        self._places = list(places)
        self._activities = list(activities)

    @property
    def source(self) -> InformationSource:
        return InformationSource(data_source="fake_source", is_live=False)

    async def find_places(self, criteria):
        return list(self._places)

    async def find_activities(self, criteria):
        return list(self._activities)

    async def get_place(self, place_id):
        return next((place for place in self._places if place.id == place_id), None)

    async def get_activity(self, activity_id):
        return next((activity for activity in self._activities if activity.id == activity_id), None)


class FakePlanRepository:
    """Minimal in-memory aggregate store for selection tests."""

    def __init__(self, plan: Plan | None = None) -> None:
        self._plans: dict[UUID, Plan] = {}
        if plan is not None:
            self._plans[plan.id] = plan

    async def get(self, plan_id: UUID, user_id: UUID) -> Plan | None:
        plan = self._plans.get(plan_id)
        if plan is None or plan.user_id != user_id:
            return None
        return plan

    async def create_item(self, user_id: UUID, plan_id: UUID, item) -> Plan | None:
        plan = await self.get(plan_id, user_id)
        if plan is None:
            return None
        plan.items.append(item)
        return item


def _place(place_id=PLACE_ID) -> Place:
    return Place(id=place_id, name="Harbour Market Hall", location="Cape Town",
                 category=InformationCategory.FOOD, description="Fixture venue.",
                 price_from=Decimal("90"))


def _activity(activity_id=ACTIVITY_ID) -> Activity:
    return Activity(id=activity_id, name="Harbour food tasting", category=InformationCategory.FOOD,
                    description="Fixture activity.", cost=Decimal("180"), duration_minutes=90,
                    location="Cape Town")


def _plan(user_id: UUID | None = None, *, status=PlanStatus.DRAFT,
          constraints=None, context=None) -> Plan:
    owner = user_id or uuid4()
    plan = Plan(user_id=owner, intention="Test plan")
    plan.status = status
    plan.context = context if context is not None else PlanningContext(plan_id=plan.id, location="Cape Town")
    if constraints is not None:
        plan.constraints = constraints
    return plan


def _service(plan: Plan, provider: FakeProvider) -> tuple[PlanSelectionService, FakePlanRepository]:
    repository = FakePlanRepository(plan)
    plans = PlanningService(repository)
    information = PlanningInformationService(provider)
    return PlanSelectionService(plans, information), repository


@pytest.mark.asyncio
async def test_select_valid_place_creates_food_plan_item() -> None:
    plan = _plan()
    service, repository = _service(plan, FakeProvider(places=[_place()]))

    item = await service.select_option(plan.user_id, plan.id, PLACE_ID, CandidateType.PLACE)

    assert item.name == "Harbour Market Hall"
    assert item.item_type is PlanItemType.FOOD
    assert item.estimated_cost == Decimal("90")
    assert item.location == "Cape Town"
    assert item.plan_id == plan.id


@pytest.mark.asyncio
async def test_select_valid_activity_creates_activity_plan_item() -> None:
    plan = _plan()
    service, _ = _service(plan, FakeProvider(activities=[_activity()]))

    item = await service.select_option(plan.user_id, plan.id, ACTIVITY_ID, CandidateType.ACTIVITY)

    assert item.name == "Harbour food tasting"
    assert item.item_type is PlanItemType.FOOD
    assert item.estimated_cost == Decimal("180")


@pytest.mark.asyncio
async def test_position_appends_after_existing_final_item() -> None:
    plan = _plan()
    plan.items.append(_existing_item(plan, position=0))
    plan.items.append(_existing_item(plan, position=1))
    service, _ = _service(plan, FakeProvider(places=[_place()]))

    item = await service.select_option(plan.user_id, plan.id, PLACE_ID, CandidateType.PLACE)

    assert item.position == 2


@pytest.mark.asyncio
async def test_explicit_position_is_preserved() -> None:
    plan = _plan()
    plan.items.append(_existing_item(plan, position=5))
    service, _ = _service(plan, FakeProvider(places=[_place()]))

    item = await service.select_option(plan.user_id, plan.id, PLACE_ID, CandidateType.PLACE, position=3)

    assert item.position == 3


@pytest.mark.asyncio
async def test_budget_summary_reflects_selected_item() -> None:
    budget = Constraint(plan_id=uuid4(), type=ConstraintType.BUDGET_MAX, value="R500", numeric_value=Decimal("500"))
    plan = _plan(constraints=[budget])
    budget.plan_id = plan.id
    service, _ = _service(plan, FakeProvider(activities=[_activity()]))

    await service.select_option(plan.user_id, plan.id, ACTIVITY_ID, CandidateType.ACTIVITY)

    summary = plan.budget_summary()
    assert summary.total_planned_cost == Decimal("180")
    assert summary.remaining_budget == Decimal("320")
    assert summary.is_over_budget is False


@pytest.mark.asyncio
async def test_over_budget_selection_is_representable_and_not_rejected() -> None:
    budget = Constraint(plan_id=uuid4(), type=ConstraintType.BUDGET_MAX, value="R100", numeric_value=Decimal("100"))
    plan = _plan(constraints=[budget])
    budget.plan_id = plan.id
    service, _ = _service(plan, FakeProvider(activities=[_activity()]))

    item = await service.select_option(plan.user_id, plan.id, ACTIVITY_ID, CandidateType.ACTIVITY)

    assert item.estimated_cost == Decimal("180")
    assert plan.budget_summary().is_over_budget is True


@pytest.mark.asyncio
async def test_archived_plan_is_rejected() -> None:
    plan = _plan(status=PlanStatus.ARCHIVED)
    service, _ = _service(plan, FakeProvider(places=[_place()]))

    with pytest.raises(ValueError, match="Archived"):
        await service.select_option(plan.user_id, plan.id, PLACE_ID, CandidateType.PLACE)


@pytest.mark.asyncio
async def test_inaccessible_plan_is_rejected_as_not_found() -> None:
    plan = _plan()
    service, _ = _service(plan, FakeProvider(places=[_place()]))

    with pytest.raises(PlanningNotFoundError):
        await service.select_option(uuid4(), plan.id, PLACE_ID, CandidateType.PLACE)


@pytest.mark.asyncio
async def test_unknown_option_is_rejected() -> None:
    plan = _plan()
    service, _ = _service(plan, FakeProvider(places=[_place()]))

    with pytest.raises(OptionNotFoundError):
        await service.select_option(plan.user_id, plan.id, uuid4(), CandidateType.PLACE)


@pytest.mark.asyncio
async def test_cross_type_option_is_rejected() -> None:
    plan = _plan()
    service, _ = _service(plan, FakeProvider(activities=[_activity()]))

    with pytest.raises(OptionNotFoundError):
        await service.select_option(plan.user_id, plan.id, ACTIVITY_ID, CandidateType.PLACE)


@pytest.mark.asyncio
async def test_start_time_derives_end_time_from_activity_duration() -> None:
    plan = _plan()
    service, _ = _service(plan, FakeProvider(activities=[_activity()]))
    start = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)

    item = await service.select_option(plan.user_id, plan.id, ACTIVITY_ID, CandidateType.ACTIVITY, start_time=start)

    assert item.start_time == start
    assert item.end_time == start.replace(hour=11, minute=30)
    assert item.duration_minutes == 90


def test_criteria_from_plan_uses_context_and_budget_constraint() -> None:
    budget = Constraint(plan_id=uuid4(), type=ConstraintType.BUDGET_MAX, value="R500", numeric_value=Decimal("500"))
    plan = _plan(context=PlanningContext(plan_id=uuid4(), location="Cape Town", group_size=4), constraints=[budget])
    budget.plan_id = plan.id
    plan.context.plan_id = plan.id

    criteria = criteria_from_plan(plan)

    assert criteria.location == "Cape Town"
    assert criteria.group_size == 4
    assert criteria.maximum_cost == Decimal("500")


def test_criteria_from_plan_derives_category_group_and_duration_constraints() -> None:
    plan_id = uuid4()
    budget = Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="R300", numeric_value=Decimal("300"))
    pref = Constraint(plan_id=plan_id, type=ConstraintType.PREFERENCE, value="food")
    duration = Constraint(plan_id=plan_id, type=ConstraintType.TIME_MAX, value="90", numeric_value=Decimal("90"))
    group = Constraint(plan_id=plan_id, type=ConstraintType.GROUP_SIZE, value="6", numeric_value=Decimal("6"))
    plan = _plan(
        context=PlanningContext(plan_id=plan_id, location="Sea Point", group_size=2),
        constraints=[budget, pref, duration, group],
    )
    plan.id = plan_id

    criteria = criteria_from_plan(plan)

    assert criteria.location == "Sea Point"
    assert criteria.category == InformationCategory.FOOD
    assert criteria.maximum_cost == Decimal("300")
    assert criteria.group_size == 6
    assert criteria.maximum_duration_minutes == 90


def _existing_item(plan: Plan, position: int) -> PlanItem:
    return PlanItem(plan_id=plan.id, name="Existing", item_type=PlanItemType.OTHER, position=position)
