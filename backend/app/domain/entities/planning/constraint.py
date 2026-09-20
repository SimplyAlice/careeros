from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class ConstraintType(str, Enum):
    BUDGET_MAX = "budget_max"
    BUDGET_MIN = "budget_min"
    TIME_MAX = "time_max"
    TIME_MIN = "time_min"
    DISTANCE_MAX = "distance_max"
    GROUP_SIZE = "group_size"
    PREFERENCE = "preference"
    REQUIREMENT = "requirement"


@dataclass
class Constraint:
    plan_id: UUID
    type: ConstraintType
    value: str
    id: UUID = field(default_factory=uuid4)
    numeric_value: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Constraint value cannot be empty.")

        if self.numeric_value is not None and self.numeric_value < 0:
            raise ValueError("Constraint numeric value cannot be negative.")
