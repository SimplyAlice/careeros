from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from app.domain.entities.planning.adaptation import PlanAdaptation
from app.domain.entities.planning.information import FreshnessKind


class LiveSignalType(str, Enum):
    WEATHER = "weather"
    OPERATING_HOURS = "operating_hours"
    VENUE_STATUS = "venue_status"
    EVENT_STATUS = "event_status"
    AVAILABILITY = "availability"
    PRICE = "price"


class LiveChangeType(str, Enum):
    VENUE_CLOSED = "venue_closed"
    CLOSING_EARLY = "closing_early"
    WEATHER_UNSUITABLE = "weather_unsuitable"
    EVENT_CANCELLED = "event_cancelled"
    EVENT_RESCHEDULED = "event_rescheduled"
    CAPACITY_UNAVAILABLE = "capacity_unavailable"
    PRICE_BUDGET_OVERAGE = "price_budget_overage"
    INFORMATIONAL = "informational"
    NONE = "none"


class PlanHealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ACTION_REQUIRED = "action_required"


@dataclass(frozen=True)
class LiveSignal:
    """An observed real-world signal pertinent to a plan or a specific stop."""

    source: str
    signal_type: LiveSignalType
    observed_at: datetime
    freshness: FreshnessKind
    target_name: str
    target_item_id: UUID | None = None
    change_type: LiveChangeType = LiveChangeType.NONE
    current_value: Any = None
    previous_value: Any = None
    is_meaningful_change: bool = False
    message: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Live signal source cannot be empty.")
        if not self.target_name.strip():
            raise ValueError("Live signal target name cannot be empty.")


@dataclass(frozen=True)
class PlanHealthCheckResult:
    """Aggregate health assessment of an existing plan grounded in live signals."""

    plan_id: UUID
    health_status: PlanHealthStatus
    headline: str
    narrative: str
    signals: list[LiveSignal]
    checked_at: datetime
    recommended_adaptation_prompt: str | None = None
    proposed_adaptation: PlanAdaptation | None = None

    def __post_init__(self) -> None:
        if not self.headline.strip():
            raise ValueError("Health check headline cannot be empty.")
        if not self.narrative.strip():
            raise ValueError("Health check narrative cannot be empty.")
