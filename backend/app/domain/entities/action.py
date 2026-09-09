from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class ActionType(str, Enum):
    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    ACKNOWLEDGE_INCIDENT = "acknowledge_incident"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class Action:
    id: UUID
    service_id: UUID
    action_type: ActionType
    reason: str
    status: ActionStatus = ActionStatus.PENDING

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("Action reason cannot be empty.")