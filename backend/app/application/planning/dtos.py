from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.planning.constraint import ConstraintType


@dataclass(frozen=True)
class ConstraintInput:
    type: ConstraintType
    value: str
    numeric_value: Decimal | None = None


@dataclass(frozen=True)
class CreatePlanData:
    user_id: UUID
    intention: str
    title: str | None = None
    location: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    group_size: int = 1
    transport_mode: str | None = None
    constraints: list[ConstraintInput] | None = None
