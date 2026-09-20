from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.planning.constraint import Constraint, ConstraintType


def test_budget_constraint_can_be_created() -> None:
    constraint = Constraint(
        plan_id=uuid4(),
        type=ConstraintType.BUDGET_MAX,
        value="1500",
        numeric_value=Decimal("1500"),
    )

    assert constraint.type == ConstraintType.BUDGET_MAX
    assert constraint.numeric_value == Decimal("1500")


def test_preference_constraint_can_be_created() -> None:
    constraint = Constraint(
        plan_id=uuid4(),
        type=ConstraintType.PREFERENCE,
        value="cute atmosphere",
    )

    assert constraint.type == ConstraintType.PREFERENCE
    assert constraint.value == "cute atmosphere"


def test_constraint_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="Constraint value cannot be empty"):
        Constraint(
            plan_id=uuid4(),
            type=ConstraintType.REQUIREMENT,
            value="   ",
        )


def test_constraint_rejects_negative_numeric_value() -> None:
    with pytest.raises(
        ValueError,
        match="Constraint numeric value cannot be negative",
    ):
        Constraint(
            plan_id=uuid4(),
            type=ConstraintType.BUDGET_MAX,
            value="-100",
            numeric_value=Decimal("-100"),
        )