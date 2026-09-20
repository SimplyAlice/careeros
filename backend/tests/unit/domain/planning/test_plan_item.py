from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


def test_food_plan_item_can_be_created() -> None:
    item = PlanItem(
        plan_id=uuid4(),
        name="Dinner",
        item_type=PlanItemType.FOOD,
        estimated_cost=Decimal("450"),
        location="Cape Town",
    )

    assert item.name == "Dinner"
    assert item.item_type == PlanItemType.FOOD
    assert item.estimated_cost == Decimal("450")


def test_plan_item_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="Plan item name cannot be empty"):
        PlanItem(
            plan_id=uuid4(),
            name="   ",
            item_type=PlanItemType.ACTIVITY,
        )


def test_plan_item_rejects_negative_cost() -> None:
    with pytest.raises(ValueError, match="Estimated cost cannot be negative"):
        PlanItem(
            plan_id=uuid4(),
            name="Dinner",
            item_type=PlanItemType.FOOD,
            estimated_cost=Decimal("-50"),
        )


def test_plan_item_rejects_invalid_time_range() -> None:
    start = datetime(2026, 9, 26, 18, 0)

    with pytest.raises(
        ValueError,
        match="End time cannot be before start time",
    ):
        PlanItem(
            plan_id=uuid4(),
            name="Dinner",
            item_type=PlanItemType.FOOD,
            start_time=start,
            end_time=start - timedelta(hours=1),
        )