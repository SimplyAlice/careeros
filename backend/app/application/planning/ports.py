from typing import Protocol

from app.application.planning.dtos import CreatePlanData
from app.domain.entities.planning.plan import Plan


class PlanRepository(Protocol):
    async def create(self, data: CreatePlanData) -> Plan:
        """Persist a plan and its initial planning context/constraints."""
        ...
