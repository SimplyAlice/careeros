from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class ExecutionActionType(str, Enum):
    OPEN_WEBSITE = "open_website"
    DIRECTIONS = "directions"
    CALL = "call"
    RESERVE = "reserve"
    ADD_TO_CALENDAR = "add_to_calendar"
    MARK_COMPLETE = "mark_complete"


class ExecutionActionStatus(str, Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class PlanItemStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PlanExecutionStatus(str, Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True)
class ExecutionAction:
    """An action that can be performed for a plan item."""

    id: str
    item_id: UUID
    action_type: ExecutionActionType
    label: str
    target_url: str | None = None
    is_available: bool = True
    status: ExecutionActionStatus = ExecutionActionStatus.AVAILABLE
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Execution action ID cannot be empty.")
        if not self.label.strip():
            raise ValueError("Execution action label cannot be empty.")


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of attempting or completing an execution action."""

    action_type: ExecutionActionType
    status: ExecutionActionStatus
    message: str
    target_url: str | None = None
    item_status: str = PlanItemStatus.PLANNED.value
    plan_status: str = PlanExecutionStatus.READY.value

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Execution result message cannot be empty.")
