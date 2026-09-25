from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class ConstraintKind(str, Enum):
    HARD_CONSTRAINT = "hard_constraint"
    SOFT_PREFERENCE = "soft_preference"
    CONTEXT = "context"
    UNKNOWN = "unknown"


class BudgetStyle(str, Enum):
    TOTAL = "total"
    PER_PERSON = "per_person"
    APPROXIMATE = "approximate"
    HARD_CEILING = "hard_ceiling"
    FLEXIBLE_STRETCH = "flexible_stretch"
    PRIORITY_CHEAP = "priority_cheap"
    NONE = "none"


class EvidenceProvenance(str, Enum):
    VERIFIED = "verified"
    PROBABLE = "probable"
    UNKNOWN = "unknown"
    CONTRADICTION = "contradiction"


class TravelProviderKind(str, Enum):
    LIVE = "live"
    STATIC_ESTIMATE = "static_estimate"
    CONSERVATIVE_FALLBACK = "conservative_fallback"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BudgetConstraint:
    """Nuanced budget intelligence representation."""

    amount: Decimal | None = None
    style: BudgetStyle = BudgetStyle.NONE
    stretch_amount: Decimal | None = None
    per_person: bool = False
    priority_note: str | None = None

    def effective_limit(self, group_size: int = 1) -> Decimal | None:
        """Calculate effective total limit for candidate evaluation."""
        if self.amount is None:
            return None
        if self.per_person and group_size > 1:
            return self.amount * Decimal(group_size)
        return self.amount


@dataclass(frozen=True)
class TemporalConstraint:
    """Nuanced temporal intelligence representation."""

    date_spec: str | None = None
    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    deadline: str | None = None
    time_window: str | None = None
    duration_limit_minutes: int | None = None
    confidence: str = "unknown"


@dataclass(frozen=True)
class TravelEstimate:
    """Travel time and feasibility estimate between itinerary stops."""

    origin: str | None
    destination: str | None
    duration_minutes: int
    provider_kind: TravelProviderKind = TravelProviderKind.CONSERVATIVE_FALLBACK
    confidence: str = "estimated"
