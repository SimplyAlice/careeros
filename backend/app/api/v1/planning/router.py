from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_planning_service
from app.api.v1.auth import get_current_user
from app.application.planning.dtos import ConstraintInput, CreatePlanData
from app.application.planning.planning_service import PlanningService
from app.domain.entities.planning.constraint import ConstraintType
from app.infrastructure.db.models import User

router = APIRouter(prefix="/planning", tags=["planning"])


class ConstraintWrite(BaseModel):
    type: ConstraintType
    value: str = Field(..., min_length=1)
    numeric_value: Decimal | None = Field(default=None, ge=0)


class CreatePlanRequest(BaseModel):
    intention: str = Field(..., min_length=1, max_length=5000)
    title: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    start_time: datetime | None = None
    end_time: datetime | None = None
    group_size: int = Field(default=1, ge=1)
    transport_mode: str | None = Field(default=None, max_length=100)
    constraints: list[ConstraintWrite] = Field(default_factory=list)

    def to_data(self, user_id: UUID) -> CreatePlanData:
        return CreatePlanData(
            user_id=user_id,
            intention=self.intention,
            title=self.title,
            location=self.location,
            start_time=self.start_time,
            end_time=self.end_time,
            group_size=self.group_size,
            transport_mode=self.transport_mode,
            constraints=[
                ConstraintInput(
                    type=item.type,
                    value=item.value,
                    numeric_value=item.numeric_value,
                )
                for item in self.constraints
            ],
        )


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    intention: str
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


@router.post(
    "/plans",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a planning request",
)
async def create_plan(
    body: CreatePlanRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanRead:
    plan = await service.create_plan(body.to_data(current_user.id))
    return PlanRead.model_validate(plan)
