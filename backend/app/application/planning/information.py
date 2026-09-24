from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.application.planning.ports import PlanningInformationProvider
from app.domain.entities.planning.information import Activity, InformationCategory, InformationSource, Place


@dataclass(frozen=True)
class OptionSearchCriteria:
    location: str | None = None
    category: InformationCategory | None = None
    maximum_cost: Decimal | None = None
    group_size: int | None = None
    maximum_duration_minutes: int | None = None

    def __post_init__(self) -> None:
        if self.maximum_cost is not None and self.maximum_cost < 0:
            raise ValueError("Maximum cost cannot be negative.")
        if self.group_size is not None and self.group_size < 1:
            raise ValueError("Group size must be at least 1.")
        if self.maximum_duration_minutes is not None and self.maximum_duration_minutes <= 0:
            raise ValueError("Maximum duration must be positive.")


class PlanningInformationService:
    """Retrieves provider-neutral planning options for a future decision engine."""

    def __init__(self, provider: PlanningInformationProvider) -> None:
        self._provider = provider

    @property
    def source(self) -> InformationSource:
        """Metadata describing whether the active provider is live or a fixture."""
        return self._provider.source

    async def search_places(self, criteria: OptionSearchCriteria) -> list[Place]:
        return await self._provider.find_places(criteria)

    async def search_activities(self, criteria: OptionSearchCriteria) -> list[Activity]:
        return await self._provider.find_activities(criteria)

    async def get_place(self, place_id: UUID) -> Place | None:
        """Authoritative lookup of a single place by id."""
        return await self._provider.get_place(place_id)

    async def get_activity(self, activity_id: UUID) -> Activity | None:
        """Authoritative lookup of a single activity by id."""
        return await self._provider.get_activity(activity_id)
