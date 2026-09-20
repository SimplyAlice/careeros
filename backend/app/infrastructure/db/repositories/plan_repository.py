from sqlalchemy.ext.asyncio import AsyncSession

from app.application.planning.dtos import CreatePlanData
from app.application.planning.ports import PlanRepository
from app.domain.entities.planning.plan import Plan
from app.infrastructure.db.models.constraint import ConstraintModel
from app.infrastructure.db.models.plan import PlanModel
from app.infrastructure.db.models.planning_context import PlanningContextModel


class SqlAlchemyPlanRepository(PlanRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: CreatePlanData) -> Plan:
        plan = Plan(
            user_id=data.user_id,
            intention=data.intention,
            title=data.title,
        )

        model = PlanModel(
            id=plan.id,
            user_id=plan.user_id,
            intention=plan.intention,
            title=plan.title,
            status=plan.status,
        )

        model.context = PlanningContextModel(
            plan_id=plan.id,
            location=data.location,
            start_time=data.start_time,
            end_time=data.end_time,
            group_size=data.group_size,
            transport_mode=data.transport_mode,
        )

        model.constraints = [
            ConstraintModel(
                plan_id=plan.id,
                type=constraint.type,
                value=constraint.value,
                numeric_value=constraint.numeric_value,
            )
            for constraint in (data.constraints or [])
        ]

        self.session.add(model)
        await self.session.flush()

        return plan
