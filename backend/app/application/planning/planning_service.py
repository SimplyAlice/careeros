from __future__ import annotations

from typing import Any
from uuid import UUID

from app.application.planning.dtos import ConstraintInput, CreatePlanData, PlanItemData, PlanningIntent
from app.application.planning.errors import PlanItemNotFoundError, PlanningNotFoundError
from app.application.planning.ports import PlanRepository
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.plan import Plan
from app.domain.entities.planning.plan_item import PlanItem


class PlanningService:
    def __init__(self, repository: PlanRepository) -> None:
        self._repository = repository

    async def create_plan(self, data: CreatePlanData) -> Plan:
        plan = Plan(user_id=data.user_id, intention=data.intention, title=data.title)
        plan.replace_context(_context_from_data(plan.id, data))
        plan.replace_constraints(_constraints_from_inputs(plan.id, data.constraints or []))
        return await self._repository.create(plan)

    async def get_plan(self, user_id: UUID, plan_id: UUID) -> Plan:
        plan = await self._repository.get(plan_id, user_id)
        if plan is None:
            raise PlanningNotFoundError("Plan not found.")
        return plan

    async def list_plans(self, user_id: UUID) -> list[Plan]:
        return await self._repository.list_for_user(user_id)

    async def update_plan(self, user_id: UUID, plan_id: UUID, changes: dict[str, Any]) -> Plan:
        plan = await self.get_plan(user_id, plan_id)
        plan_changes = {key: value for key, value in changes.items() if key in {"intention", "title", "status"}}
        if plan_changes:
            plan.apply_patch(plan_changes)
        if "context" in changes:
            context_data = changes["context"]
            current = plan.context or PlanningContext(plan_id=plan.id)
            plan.replace_context(PlanningContext(
                plan_id=plan.id,
                location=context_data.get("location", current.location),
                start_time=context_data.get("start_time", current.start_time),
                end_time=context_data.get("end_time", current.end_time),
                group_size=context_data.get("group_size", current.group_size),
                transport_mode=context_data.get("transport_mode", current.transport_mode),
            ))
        if "constraints" in changes:
            constraints: list[ConstraintInput] = changes["constraints"]
            plan.replace_constraints(_constraints_from_inputs(plan.id, constraints))
        return await self._repository.update(plan)

    async def delete_plan(self, user_id: UUID, plan_id: UUID) -> None:
        plan = await self.get_plan(user_id, plan_id)
        plan.ensure_mutable()
        if not await self._repository.delete(plan_id, user_id):
            raise PlanningNotFoundError("Plan not found.")

    async def create_item(self, user_id: UUID, plan_id: UUID, data: PlanItemData) -> PlanItem:
        (await self.get_plan(user_id, plan_id)).ensure_mutable()
        position = 0 if data.position is None else data.position
        item = PlanItem(plan_id=plan_id, name=data.name, item_type=data.item_type, description=data.description,
                        start_time=data.start_time, end_time=data.end_time, estimated_cost=data.estimated_cost,
                        location=data.location, position=position)
        created = await self._repository.create_item(user_id, plan_id, item)
        if created is None:
            raise PlanningNotFoundError("Plan not found.")
        return created

    async def add_item(self, user_id: UUID, plan_id: UUID, item: PlanItem) -> PlanItem:
        """Persist an already-built PlanItem after enforcing plan mutability.

        Used by explicit selection flows. The PlanItem is authoritative
        input; this method only enforces aggregate rules and appends it.
        """
        if item.plan_id != plan_id:
            raise ValueError("Plan item belongs to another plan.")
        (await self.get_plan(user_id, plan_id)).ensure_mutable()
        created = await self._repository.create_item(user_id, plan_id, item)
        if created is None:
            raise PlanningNotFoundError("Plan not found.")
        return created

    async def list_items(self, user_id: UUID, plan_id: UUID) -> list[PlanItem]:
        items = await self._repository.list_items(user_id, plan_id)
        if items is None:
            raise PlanningNotFoundError("Plan not found.")
        return items

    async def update_item(self, user_id: UUID, plan_id: UUID, item_id: UUID, changes: dict[str, Any]) -> PlanItem:
        (await self.get_plan(user_id, plan_id)).ensure_mutable()
        item = await self._repository.get_item(user_id, plan_id, item_id)
        if item is None:
            raise PlanItemNotFoundError("Plan item not found.")
        item.apply_patch(changes)
        updated = await self._repository.update_item(user_id, plan_id, item)
        if updated is None:
            raise PlanItemNotFoundError("Plan item not found.")
        return updated

    async def delete_item(self, user_id: UUID, plan_id: UUID, item_id: UUID) -> None:
        plan = await self.get_plan(user_id, plan_id)
        plan.ensure_mutable()
        if not await self._repository.delete_item(user_id, plan_id, item_id):
            raise PlanItemNotFoundError("Plan item not found.")

    async def create_plan_from_intent(self, intent: PlanningIntent) -> Plan:
        constraints: list[ConstraintInput] = []
        if intent.budget_max is not None:
            constraints.append(ConstraintInput(type=ConstraintType.BUDGET_MAX, value=f"R{intent.budget_max}", numeric_value=intent.budget_max))
        return await self.create_plan(CreatePlanData(user_id=intent.user_id, intention=intent.raw_request,
                                      location=intent.location, group_size=intent.group_size, constraints=constraints))


def _context_from_data(plan_id: UUID, data: CreatePlanData) -> PlanningContext:
    return PlanningContext(plan_id=plan_id, location=data.location, start_time=data.start_time, end_time=data.end_time,
                           group_size=data.group_size, transport_mode=data.transport_mode)


def _constraints_from_inputs(plan_id: UUID, inputs: list[ConstraintInput]) -> list[Constraint]:
    return [Constraint(plan_id=plan_id, type=item.type, value=item.value, numeric_value=item.numeric_value) for item in inputs]
