from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.plan_item import PlanItem


@dataclass(frozen=True)
class BudgetSummary:
    budget_maximum: Decimal | None
    total_planned_cost: Decimal
    remaining_budget: Decimal | None
    is_over_budget: bool


def calculate_budget(items: list[PlanItem], constraints: list[Constraint]) -> BudgetSummary:
    """Calculate a plan budget without involving persistence or HTTP concerns."""
    total = sum(
        (item.estimated_cost for item in items if item.estimated_cost is not None),
        start=Decimal("0"),
    )
    maxima = [
        constraint.numeric_value
        for constraint in constraints
        if constraint.type is ConstraintType.BUDGET_MAX and constraint.numeric_value is not None
    ]
    # Multiple maximum-budget constraints are cumulative restrictions; the most
    # restrictive value is the operative ceiling.
    maximum = min(maxima) if maxima else None
    remaining = maximum - total if maximum is not None else None
    return BudgetSummary(
        budget_maximum=maximum,
        total_planned_cost=total,
        remaining_budget=remaining,
        is_over_budget=remaining is not None and remaining < Decimal("0"),
    )
