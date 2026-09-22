from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class PlanItemType(str, Enum):
    TRANSPORT = "transport"
    ACTIVITY = "activity"
    FOOD = "food"
    ACCOMMODATION = "accommodation"
    SHOPPING = "shopping"
    SERVICE = "service"
    OTHER = "other"


@dataclass
class PlanItem:
    plan_id: UUID
    name: str
    item_type: PlanItemType
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    estimated_cost: Decimal | None = None
    location: str | None = None
    position: int = 0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Plan item name cannot be empty.")

        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("Estimated cost cannot be negative.")

        if self.position < 0:
            raise ValueError("Plan item position cannot be negative.")

        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValueError("End time cannot be before start time.")

    @property
    def duration_minutes(self) -> int | None:
        if self.start_time is None or self.end_time is None:
            return None
        return int((self.end_time - self.start_time).total_seconds() // 60)

    def apply_patch(self, changes: dict[str, object]) -> None:
        for attribute, value in changes.items():
            if attribute not in {
                "name", "item_type", "description", "start_time", "end_time",
                "estimated_cost", "location", "position",
            }:
                continue
            setattr(self, attribute, value)
        self.__post_init__()
