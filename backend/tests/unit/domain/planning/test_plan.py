from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.plan import Plan, PlanStatus


def test_plan_requires_intention() -> None:
    with pytest.raises(ValueError, match="Plan intention cannot be empty"):
        Plan(
            intention="   ",
            user_id=uuid4(),
        )


def test_plan_can_be_created() -> None:
    user_id = uuid4()

    plan = Plan(
        intention="Dinner with friends",
        user_id=user_id,
        title="Saturday Dinner",
    )

    assert plan.user_id == user_id
    assert plan.intention == "Dinner with friends"
    assert plan.title == "Saturday Dinner"
    assert plan.status == "draft"


def test_plan_title_can_be_updated() -> None:
    plan = Plan(
        intention="Go out with friends",
        user_id=uuid4(),
    )

    plan.update_title("Cape Town Saturday")

    assert plan.title == "Cape Town Saturday"


def test_plan_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="Plan title cannot be empty"):
        Plan(
            intention="Dinner",
            user_id=uuid4(),
            title="   ",
        )


def test_archived_plan_cannot_be_reactivated_or_modified() -> None:
    plan = Plan(intention="Dinner", user_id=uuid4(), status=PlanStatus.ARCHIVED)

    with pytest.raises(ValueError, match="cannot be reactivated"):
        plan.apply_patch({"status": PlanStatus.DRAFT})

    with pytest.raises(ValueError, match="cannot be modified"):
        plan.apply_patch({"title": "New title"})


def test_planning_context_defaults_to_one_person() -> None:
    context = PlanningContext(
        plan_id=uuid4(),
    )

    assert context.group_size == 1


def test_planning_context_supports_group_plans() -> None:
    context = PlanningContext(
        plan_id=uuid4(),
        location="Cape Town",
        start_time=datetime(2026, 9, 26, 14, 0),
        end_time=datetime(2026, 9, 26, 20, 0),
        group_size=4,
        transport_mode="Uber",
    )

    assert context.location == "Cape Town"
    assert context.group_size == 4
    assert context.transport_mode == "Uber"


def test_planning_context_rejects_invalid_group_size() -> None:
    with pytest.raises(ValueError, match="Group size must be at least 1"):
        PlanningContext(
            plan_id=uuid4(),
            group_size=0,
        )


def test_planning_context_rejects_end_time_before_start_time() -> None:
    start = datetime(2026, 9, 26, 20, 0)

    with pytest.raises(
        ValueError,
        match="End time cannot be before start time",
    ):
        PlanningContext(
            plan_id=uuid4(),
            start_time=start,
            end_time=start - timedelta(hours=1),
        )
