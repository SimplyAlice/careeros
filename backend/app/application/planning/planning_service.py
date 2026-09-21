from app.application.planning.dtos import ConstraintInput, CreatePlanData, PlanningIntent
from app.application.planning.ports import PlanRepository
from app.domain.entities.planning.constraint import Constraint, ConstraintType
from app.domain.entities.planning.context import PlanningContext
from app.domain.entities.planning.plan import Plan


class PlanningService:
    def __init__(self, repository: PlanRepository) -> None:
        self.repository = repository

    async def create_plan(self, data: CreatePlanData) -> Plan:
        plan = Plan(
            user_id=data.user_id,
            intention=data.intention,
            title=data.title,
        )

        PlanningContext(
            plan_id=plan.id,
            location=data.location,
            start_time=data.start_time,
            end_time=data.end_time,
            group_size=data.group_size,
            transport_mode=data.transport_mode,
        )

        for constraint in data.constraints or []:
            Constraint(
                plan_id=plan.id,
                type=constraint.type,
                value=constraint.value,
                numeric_value=constraint.numeric_value,
            )

        return await self.repository.create(data)

    async def create_plan_from_intent(self, intent: PlanningIntent) -> Plan:
        constraints: list[ConstraintInput] = []

        if intent.budget_max is not None:
            constraints.append(
                ConstraintInput(
                    type=ConstraintType.BUDGET_MAX,
                    value=f"R{intent.budget_max}",
                    numeric_value=intent.budget_max,
                )
            )

        data = CreatePlanData(
            user_id=intent.user_id,
            intention=intent.raw_request,
            location=intent.location,
            group_size=intent.group_size,
            constraints=constraints,
        )

        return await self.create_plan(data)
