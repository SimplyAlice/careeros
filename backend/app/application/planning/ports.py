from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.domain.entities.planning.information import Activity, InformationSource, Place
from app.domain.entities.planning.plan import Plan
from app.domain.entities.planning.plan_item import PlanItem

if TYPE_CHECKING:
    from app.application.planning.information import OptionSearchCriteria
    from app.domain.entities.planning.understanding import PlanningUnderstanding


class PlanningUnderstandingPort(Protocol):
    """Boundary for understanding conversational planning requests.

    Consumes a raw natural language user request and produces a structured,
    provider-neutral PlanningUnderstanding value object. Implementations may
    be deterministic, rule-based, hybrid, or LLM-driven without changing the domain
    or application callers.
    """

    async def understand(self, user_id: UUID, raw_request: str) -> PlanningUnderstanding:
        ...


class PlanRepository(Protocol):
    async def create(self, plan: Plan) -> Plan:
        ...

    async def get(self, plan_id: UUID, user_id: UUID) -> Plan | None:
        ...

    async def list_for_user(self, user_id: UUID) -> list[Plan]:
        ...

    async def update(self, plan: Plan) -> Plan:
        ...

    async def delete(self, plan_id: UUID, user_id: UUID) -> bool:
        ...

    async def create_item(self, user_id: UUID, plan_id: UUID, item: PlanItem) -> PlanItem | None:
        ...

    async def get_item(self, user_id: UUID, plan_id: UUID, item_id: UUID) -> PlanItem | None:
        ...

    async def list_items(self, user_id: UUID, plan_id: UUID) -> list[PlanItem] | None:
        ...

    async def update_item(self, user_id: UUID, plan_id: UUID, item: PlanItem) -> PlanItem | None:
        ...

    async def delete_item(self, user_id: UUID, plan_id: UUID, item_id: UUID) -> bool:
        ...


class PlanningInformationProvider(Protocol):
    """Boundary for fixture, database, or future external option sources."""

    @property
    def source(self) -> InformationSource:
        """Describes whether this provider's data is live or a fixture."""
        ...

    async def find_places(self, criteria: OptionSearchCriteria) -> list[Place]:
        ...

    async def find_activities(self, criteria: OptionSearchCriteria) -> list[Activity]:
        ...

    async def get_place(self, place_id: UUID) -> Place | None:
        """Return a single place by id, or None if it is not available."""
        ...

    async def get_activity(self, activity_id: UUID) -> Activity | None:
        """Return a single activity by id, or None if it is not available."""
        ...
