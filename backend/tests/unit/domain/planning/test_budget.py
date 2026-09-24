from decimal import Decimal
from uuid import uuid4

from app.domain.entities.planning.budget import calculate_budget
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


def test_budget_calculates_total_and_remaining_with_decimal_precision() -> None:
    plan_id = uuid4()
    summary = calculate_budget(
        [
            PlanItem(plan_id=plan_id, name="Coffee", item_type=PlanItemType.FOOD, estimated_cost=Decimal("35.50")),
            PlanItem(plan_id=plan_id, name="Museum", item_type=PlanItemType.ACTIVITY, estimated_cost=Decimal("80.25")),
        ],
        [Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="R200", numeric_value=Decimal("200"))],
    )

    assert summary.total_planned_cost == Decimal("115.75")
    assert summary.remaining_budget == Decimal("84.25")
    assert summary.is_over_budget is False


def test_budget_detects_overage_and_uses_most_restrictive_maximum() -> None:
    plan_id = uuid4()
    summary = calculate_budget(
        [PlanItem(plan_id=plan_id, name="Dinner", item_type=PlanItemType.FOOD, estimated_cost=Decimal("250"))],
        [
            Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="R500", numeric_value=Decimal("500")),
            Constraint(plan_id=plan_id, type=ConstraintType.BUDGET_MAX, value="R200", numeric_value=Decimal("200")),
        ],
    )

    assert summary.budget_maximum == Decimal("200")
    assert summary.remaining_budget == Decimal("-50")
    assert summary.is_over_budget is True


def test_budget_without_maximum_has_no_remaining_amount() -> None:
    summary = calculate_budget([], [])

    assert summary.total_planned_cost == Decimal("0")
    assert summary.budget_maximum is None
    assert summary.remaining_budget is None
    assert summary.is_over_budget is False
