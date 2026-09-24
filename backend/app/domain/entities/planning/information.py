from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class InformationCategory(str, Enum):
    FOOD = "food"
    CULTURE = "culture"
    NATURE = "nature"
    ENTERTAINMENT = "entertainment"
    WELLNESS = "wellness"
    SHOPPING = "shopping"


class FreshnessKind(str, Enum):
    LIVE = "live"
    RECENTLY_VERIFIED = "recently_verified"
    CACHED = "cached"
    FIXTURE = "fixture"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InformationSource:
    """Describes where planning options came from.

    Lets callers distinguish development fixtures from live or verified
    information without the API layer hardcoding any particular provider.
    """

    data_source: str
    is_live: bool
    attribution: str | None = None
    freshness: str = "fixture"

    def __post_init__(self) -> None:
        if not self.data_source.strip():
            raise ValueError("Information source identifier cannot be empty.")


@dataclass(frozen=True)
class Place:
    """A real-world venue reference supplied by an information provider."""

    name: str
    location: str
    category: InformationCategory
    description: str
    id: UUID = field(default_factory=uuid4)
    price_from: Decimal | None = None
    opening_hours: str | None = None
    minimum_group_size: int = 1
    maximum_group_size: int | None = None
    source: str = "development_fixture"
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    operating_status: str | None = None
    freshness: str = "fixture"
    verified_at: str | None = None
    source_url: str | None = None
    phone: str | None = None
    reservation_url: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Place name cannot be empty.")
        if not self.location.strip():
            raise ValueError("Place location cannot be empty.")
        if not self.description.strip():
            raise ValueError("Place description cannot be empty.")
        if self.price_from is not None and self.price_from < 0:
            raise ValueError("Place price cannot be negative.")
        _validate_group_range(self.minimum_group_size, self.maximum_group_size)


@dataclass(frozen=True)
class Activity:
    """A schedulable option that may be hosted at a known place."""

    name: str
    category: InformationCategory
    description: str
    duration_minutes: int
    cost: Decimal | None = None
    id: UUID = field(default_factory=uuid4)
    place_id: UUID | None = None
    location: str | None = None
    minimum_group_size: int = 1
    maximum_group_size: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    source: str = "development_fixture"
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    freshness: str = "fixture"
    verified_at: str | None = None
    source_url: str | None = None
    phone: str | None = None
    reservation_url: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Activity name cannot be empty.")
        if not self.description.strip():
            raise ValueError("Activity description cannot be empty.")
        if self.cost is not None and self.cost < 0:
            raise ValueError("Activity cost cannot be negative.")
        if self.duration_minutes <= 0:
            raise ValueError("Activity duration must be positive.")
        _validate_group_range(self.minimum_group_size, self.maximum_group_size)


def _validate_group_range(minimum: int, maximum: int | None) -> None:
    if minimum < 1:
        raise ValueError("Minimum group size must be at least 1.")
    if maximum is not None and maximum < minimum:
        raise ValueError("Maximum group size cannot be less than minimum group size.")
