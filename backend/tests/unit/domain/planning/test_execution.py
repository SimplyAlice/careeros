from __future__ import annotations

from uuid import uuid4
import pytest

from app.domain.entities.planning.execution import (
    ExecutionAction,
    ExecutionActionStatus,
    ExecutionActionType,
    ExecutionResult,
    PlanExecutionStatus,
    PlanItemStatus,
)


def test_execution_action_creation_and_defaults() -> None:
    item_id = uuid4()
    action = ExecutionAction(
        id="act-website-1",
        item_id=item_id,
        action_type=ExecutionActionType.OPEN_WEBSITE,
        label="Visit website",
        target_url="https://truth.capetown/",
    )
    assert action.id == "act-website-1"
    assert action.item_id == item_id
    assert action.action_type is ExecutionActionType.OPEN_WEBSITE
    assert action.label == "Visit website"
    assert action.target_url == "https://truth.capetown/"
    assert action.is_available is True
    assert action.status is ExecutionActionStatus.AVAILABLE


def test_execution_action_validation() -> None:
    item_id = uuid4()
    with pytest.raises(ValueError, match="Execution action ID cannot be empty"):
        ExecutionAction(
            id="   ",
            item_id=item_id,
            action_type=ExecutionActionType.OPEN_WEBSITE,
            label="Visit website",
        )

    with pytest.raises(ValueError, match="Execution action label cannot be empty"):
        ExecutionAction(
            id="act-1",
            item_id=item_id,
            action_type=ExecutionActionType.OPEN_WEBSITE,
            label="   ",
        )


def test_execution_result_creation_and_validation() -> None:
    result = ExecutionResult(
        action_type=ExecutionActionType.RESERVE,
        status=ExecutionActionStatus.IN_PROGRESS,
        message="Reservation page opened. Complete your booking on the external platform.",
        target_url="https://www.kloofstreethouse.co.za/reservations",
        item_status=PlanItemStatus.PLANNED.value,
        plan_status=PlanExecutionStatus.READY.value,
    )
    assert result.action_type is ExecutionActionType.RESERVE
    assert result.status is ExecutionActionStatus.IN_PROGRESS
    assert "Reservation page opened" in result.message

    with pytest.raises(ValueError, match="Execution result message cannot be empty"):
        ExecutionResult(
            action_type=ExecutionActionType.OPEN_WEBSITE,
            status=ExecutionActionStatus.COMPLETED,
            message="   ",
        )
