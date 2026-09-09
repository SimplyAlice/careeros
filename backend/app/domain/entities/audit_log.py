from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class AuditAction(str, Enum):
    ACTION_REQUESTED = "action_requested"
    ACTION_APPROVED = "action_approved"
    ACTION_REJECTED = "action_rejected"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"


@dataclass
class AuditLog:
    id: UUID
    action_id: UUID
    action: AuditAction
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Audit log message cannot be empty.")