from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from app.domain.entities.planning.budget import BudgetSummary, calculate_budget
from app.domain.entities.planning.constraint import Constraint
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.plan_item import PlanItem


class PlanStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


@dataclass
class Plan:
    intention: str
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    context: PlanningContext | None = None
    constraints: list[Constraint] = field(default_factory=list)
    items: list[PlanItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.intention.strip():
            raise ValueError("Plan intention cannot be empty.")

        if self.title is not None and not self.title.strip():
            raise ValueError("Plan title cannot be empty.")

        if not isinstance(self.status, PlanStatus):
            self.status = PlanStatus(self.status)

    def update_title(self, title: str) -> None:
        if not title.strip():
            raise ValueError("Plan title cannot be empty.")

        self.title = title.strip()
        self.updated_at = datetime.now(UTC)

    def apply_patch(self, changes: dict[str, object]) -> None:
        if self.status is PlanStatus.ARCHIVED and any(key != "status" for key in changes):
            raise ValueError("Archived plans cannot be modified.")
        if "intention" in changes:
            intention = changes["intention"]
            if not isinstance(intention, str) or not intention.strip():
                raise ValueError("Plan intention cannot be empty.")
            self.intention = intention.strip()
        if "title" in changes:
            title = changes["title"]
            if title is not None and (not isinstance(title, str) or not title.strip()):
                raise ValueError("Plan title cannot be empty.")
            self.title = title.strip() if isinstance(title, str) else None
        if "status" in changes:
            status = PlanStatus(changes["status"])
            if self.status is PlanStatus.ARCHIVED and status is not PlanStatus.ARCHIVED:
                raise ValueError("Archived plans cannot be reactivated.")
            self.status = status
        self.updated_at = datetime.now(UTC)

    def replace_context(self, context: PlanningContext) -> None:
        self.ensure_mutable()
        if context.plan_id != self.id:
            raise ValueError("Planning context belongs to another plan.")
        self.context = context
        self.updated_at = datetime.now(UTC)

    def replace_constraints(self, constraints: list[Constraint]) -> None:
        self.ensure_mutable()
        if any(constraint.plan_id != self.id for constraint in constraints):
            raise ValueError("Planning constraint belongs to another plan.")
        self.constraints = constraints
        self.updated_at = datetime.now(UTC)

    def budget_summary(self) -> BudgetSummary:
        return calculate_budget(self.items, self.constraints)

    def ensure_mutable(self) -> None:
        if self.status is PlanStatus.ARCHIVED:
            raise ValueError("Archived plans cannot be modified.")
