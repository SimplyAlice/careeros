from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.planning.dtos import PlanningIntent
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.constraint import ConstraintType


class FakePlanRepository:
    def __init__(self) -> None:
        self.created_data = None

    async def create(self, data):
        self.created_data = data
        return type(
            "FakePlan",
            (),
            {
                "id": uuid4(),
                "user_id": data.user_id,
                "intention": data.intention,
                "title": data.title,
            },
        )()


@pytest.mark.asyncio
async def test_create_plan_from_intent_builds_structured_plan_data() -> None:
    repository = FakePlanRepository()
    service = PlanningService(repository)

    user_id = uuid4()
    intent = PlanningIntent(
        user_id=user_id,
        raw_request="I want a fun Saturday with 3 friends, R800 total, somewhere in Cape Town.",
        goal="I want a fun Saturday with 3 friends, R800 total, somewhere in Cape Town.",
        location="Cape Town",
        group_size=4,
        budget_max=Decimal("800"),
    )

    await service.create_plan_from_intent(intent)

    assert repository.created_data is not None
    assert repository.created_data.user_id == user_id
    assert repository.created_data.intention == intent.raw_request
    assert repository.created_data.location == "Cape Town"
    assert repository.created_data.group_size == 4

    assert repository.created_data.constraints is not None
    assert len(repository.created_data.constraints) == 1

    budget = repository.created_data.constraints[0]
    assert budget.type == ConstraintType.BUDGET_MAX
    assert budget.value == "R800"
    assert budget.numeric_value == Decimal("800")
