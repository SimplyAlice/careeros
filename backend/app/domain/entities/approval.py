from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Approval:
    id: UUID
    action_id: UUID
    status: ApprovalStatus = ApprovalStatus.PENDING

    def approve(self) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError("Only pending approvals can be approved.")

        self.status = ApprovalStatus.APPROVED

    def reject(self) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError("Only pending approvals can be rejected.")

        self.status = ApprovalStatus.REJECTED