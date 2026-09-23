from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_intent_interpreter,
    get_plan_selection_service,
    get_planning_decision_service,
    get_planning_information_service,
    get_planning_service,
    get_planning_understanding_service,
)
from app.api.v1.auth import get_current_user
from app.api.v1.planning.information import DecisionCandidateRead, RecommendationResponse
from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.dtos import ConstraintInput, CreatePlanData, PlanItemData
from app.application.planning.errors import OptionNotFoundError, PlanItemNotFoundError, PlanningNotFoundError
from app.application.planning.information import PlanningInformationService
from app.application.planning.intent_interpreter import IntentInterpreter
from app.application.planning.planning_service import PlanningService
from app.application.planning.ports import PlanningUnderstandingPort
from app.application.planning.selection_service import PlanSelectionService, criteria_from_plan
from app.application.planning.understanding_service import DeterministicUnderstandingEngine
from app.domain.entities.planning.constraint import ConstraintType
from app.domain.entities.planning.decision import CandidateType
from app.domain.entities.planning.plan import Plan, PlanStatus
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType
from app.domain.entities.planning.understanding import PlanningUnderstanding
from app.infrastructure.db.models import User

router = APIRouter(prefix="/planning", tags=["planning"])


class ConstraintWrite(BaseModel):
    type: ConstraintType
    value: str = Field(..., min_length=1)
    numeric_value: Decimal | None = Field(default=None, ge=0)

    def to_input(self) -> ConstraintInput:
        return ConstraintInput(type=self.type, value=self.value, numeric_value=self.numeric_value)


class ContextWrite(BaseModel):
    location: str | None = Field(default=None, max_length=255)
    start_time: datetime | None = None
    end_time: datetime | None = None
    group_size: int = Field(default=1, ge=1)
    transport_mode: str | None = Field(default=None, max_length=100)

    def to_changes(self) -> dict[str, object]:
        return self.model_dump()


class ContextPatch(BaseModel):
    location: str | None = Field(default=None, max_length=255)
    start_time: datetime | None = None
    end_time: datetime | None = None
    group_size: int | None = Field(default=None, ge=1)
    transport_mode: str | None = Field(default=None, max_length=100)

    def to_changes(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True)


class CreatePlanRequest(ContextWrite):
    intention: str = Field(..., min_length=1, max_length=5000)
    title: str | None = Field(default=None, max_length=255)
    constraints: list[ConstraintWrite] = Field(default_factory=list)

    def to_data(self, user_id: UUID) -> CreatePlanData:
        return CreatePlanData(user_id=user_id, intention=self.intention, title=self.title, location=self.location,
                              start_time=self.start_time, end_time=self.end_time, group_size=self.group_size,
                              transport_mode=self.transport_mode, constraints=[item.to_input() for item in self.constraints])


class PlanPatchRequest(BaseModel):
    intention: str | None = Field(default=None, min_length=1, max_length=5000)
    title: str | None = Field(default=None, max_length=255)
    status: PlanStatus | None = None
    context: ContextPatch | None = None
    constraints: list[ConstraintWrite] | None = None

    def to_changes(self) -> dict[str, object]:
        changes: dict[str, object] = {}
        if "intention" in self.model_fields_set:
            changes["intention"] = self.intention
        if "title" in self.model_fields_set:
            changes["title"] = self.title
        if "status" in self.model_fields_set:
            changes["status"] = self.status
        if "context" in self.model_fields_set and self.context is not None:
            changes["context"] = self.context.to_changes()
        if "constraints" in self.model_fields_set:
            changes["constraints"] = [item.to_input() for item in self.constraints or []]
        return changes


class PlanItemCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    item_type: PlanItemType
    description: str | None = Field(default=None, max_length=5000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=255)
    position: int | None = Field(default=None, ge=0)

    def to_data(self) -> PlanItemData:
        return PlanItemData(**self.model_dump())


class PlanItemPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    item_type: PlanItemType | None = None
    description: str | None = Field(default=None, max_length=5000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=255)
    position: int | None = Field(default=None, ge=0)

    def to_changes(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True)


class UnderstandingRead(BaseModel):
    goal: str
    occasion: str | None = None
    people_count: int | None = None
    relationship_context: str | None = None
    date_spec: str | None = None
    time_window: str | None = None
    location: str | None = None
    location_is_inferred: bool = False
    budget_amount: Decimal | None = None
    budget_kind: str = "none"
    preferences: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    activity_types: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_understanding(cls, u: PlanningUnderstanding) -> UnderstandingRead:
        return cls(
            goal=u.goal,
            occasion=u.occasion,
            people_count=u.people_count,
            relationship_context=u.relationship_context,
            date_spec=u.date_spec,
            time_window=u.time_window,
            location=u.location,
            location_is_inferred=u.location_is_inferred,
            budget_amount=u.budget_amount,
            budget_kind=u.budget_kind.value,
            preferences=list(u.preferences),
            exclusions=list(u.exclusions),
            activity_types=[cat.value for cat in u.activity_types],
            ambiguities=list(u.ambiguities),
            provenance=dict(u.provenance),
        )


class PlanModifyRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=5000)


class CreatePlanFromIntentRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=5000)


class SelectOptionRequest(BaseModel):
    """Explicitly select an information-layer option to add to a plan."""

    option_id: UUID
    option_type: CandidateType
    position: int | None = Field(default=None, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None


class ContextRead(BaseModel):
    location: str | None
    start_time: datetime | None
    end_time: datetime | None
    group_size: int
    transport_mode: str | None


class ConstraintRead(BaseModel):
    id: UUID
    type: ConstraintType
    value: str
    numeric_value: Decimal | None


class PlanItemRead(BaseModel):
    id: UUID
    name: str
    item_type: PlanItemType
    description: str | None
    start_time: datetime | None
    end_time: datetime | None
    duration_minutes: int | None
    estimated_cost: Decimal | None
    location: str | None
    position: int

    @classmethod
    def from_item(cls, item: PlanItem) -> PlanItemRead:
        return cls(id=item.id, name=item.name, item_type=item.item_type, description=item.description,
                   start_time=item.start_time, end_time=item.end_time, duration_minutes=item.duration_minutes,
                   estimated_cost=item.estimated_cost, location=item.location, position=item.position)


class BudgetRead(BaseModel):
    budget_maximum: Decimal | None
    total_planned_cost: Decimal
    remaining_budget: Decimal | None
    is_over_budget: bool


class PlanRead(BaseModel):
    id: UUID
    intention: str
    title: str | None
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    context: ContextRead | None
    constraints: list[ConstraintRead]
    items: list[PlanItemRead]
    budget: BudgetRead
    understanding: UnderstandingRead | None = None

    @classmethod
    def from_plan(cls, plan: Plan, understanding: PlanningUnderstanding | None = None) -> PlanRead:
        context = None if plan.context is None else ContextRead(
            location=plan.context.location, start_time=plan.context.start_time, end_time=plan.context.end_time,
            group_size=plan.context.group_size, transport_mode=plan.context.transport_mode,
        )
        budget = plan.budget_summary()
        u_read = (
            UnderstandingRead.from_understanding(understanding)
            if understanding is not None
            else _build_plan_understanding_read(plan)
        )
        return cls(
            id=plan.id,
            intention=plan.intention,
            title=plan.title,
            status=plan.status,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            context=context,
            constraints=[
                ConstraintRead(
                    id=item.id,
                    type=item.type,
                    value=item.value,
                    numeric_value=item.numeric_value,
                )
                for item in plan.constraints
            ],
            items=[PlanItemRead.from_item(item) for item in plan.items],
            budget=BudgetRead(**budget.__dict__),
            understanding=u_read,
        )


def _build_plan_understanding_read(plan: Plan) -> UnderstandingRead:
    engine = DeterministicUnderstandingEngine()
    try:
        parsed = engine.parse(plan.intention)
    except Exception:
        parsed = None

    stored_exclusions: list[str] = []
    stored_preferences: list[str] = []
    stored_occasion: str | None = None
    stored_date: str | None = None
    stored_time: str | None = None

    for c in plan.constraints:
        if c.type is ConstraintType.REQUIREMENT:
            if c.value.startswith("exclude:"):
                stored_exclusions.append(c.value.split(":", 1)[1])
            elif c.value.startswith("date:"):
                stored_date = c.value.split(":", 1)[1]
            elif c.value.startswith("time:"):
                stored_time = c.value.split(":", 1)[1]
        elif c.type is ConstraintType.PREFERENCE:
            if c.value.startswith("occasion:"):
                stored_occasion = c.value.split(":", 1)[1]
            else:
                stored_preferences.append(c.value)

    budget_c = next((c for c in plan.constraints if c.type is ConstraintType.BUDGET_MAX), None)
    budget_amount = budget_c.numeric_value if budget_c else (parsed.budget_amount if parsed else None)
    budget_kind = parsed.budget_kind.value if parsed else ("hard_max" if budget_amount else "none")

    group_size = plan.context.group_size if plan.context else (parsed.people_count if parsed else 1)
    location = plan.context.location if plan.context else (parsed.location if parsed else "Cape Town")

    merged_exclusions = list(dict.fromkeys((list(parsed.exclusions) if parsed else []) + stored_exclusions))
    merged_preferences = list(dict.fromkeys((list(parsed.preferences) if parsed else []) + stored_preferences))

    return UnderstandingRead(
        goal=plan.title or (parsed.goal if parsed else plan.intention),
        occasion=stored_occasion or (parsed.occasion if parsed else None),
        people_count=group_size,
        relationship_context=parsed.relationship_context if parsed else None,
        date_spec=stored_date or (parsed.date_spec if parsed else None),
        time_window=stored_time or (parsed.time_window if parsed else None),
        location=location,
        location_is_inferred=parsed.location_is_inferred if parsed else True,
        budget_amount=budget_amount,
        budget_kind=budget_kind,
        preferences=merged_preferences,
        exclusions=merged_exclusions,
        activity_types=[cat.value for cat in parsed.activity_types] if parsed else [],
        ambiguities=list(parsed.ambiguities) if parsed else [],
        provenance=dict(parsed.provenance) if parsed else {},
    )


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/plans", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(body: CreatePlanRequest, current_user: Annotated[User, Depends(get_current_user)],
                      service: Annotated[PlanningService, Depends(get_planning_service)]) -> PlanRead:
    try:
        return PlanRead.from_plan(await service.create_plan(body.to_data(current_user.id)))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/requests", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan_from_request(
    body: CreatePlanFromIntentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    understanding_engine: Annotated[PlanningUnderstandingPort, Depends(get_planning_understanding_service)],
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanRead:
    understanding = await understanding_engine.understand(current_user.id, body.request)
    plan = await service.create_plan_from_understanding(current_user.id, understanding)
    return PlanRead.from_plan(plan, understanding=understanding)


@router.post("/plans/{plan_id}/modifications", response_model=PlanRead)
async def modify_plan(
    plan_id: UUID,
    body: PlanModifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanRead:
    try:
        updated = await service.modify_plan(current_user.id, plan_id, body.request)
        return PlanRead.from_plan(updated)
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/plans", response_model=list[PlanRead])
async def list_plans(current_user: Annotated[User, Depends(get_current_user)],
                     service: Annotated[PlanningService, Depends(get_planning_service)]) -> list[PlanRead]:
    return [PlanRead.from_plan(plan) for plan in await service.list_plans(current_user.id)]


@router.get("/plans/{plan_id}", response_model=PlanRead)
async def get_plan(plan_id: UUID, current_user: Annotated[User, Depends(get_current_user)],
                   service: Annotated[PlanningService, Depends(get_planning_service)]) -> PlanRead:
    try:
        return PlanRead.from_plan(await service.get_plan(current_user.id, plan_id))
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/plans/{plan_id}/recommendations", response_model=RecommendationResponse)
async def get_plan_recommendations(
    plan_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlanningService, Depends(get_planning_service)],
    decision: Annotated[PlanningDecisionService, Depends(get_planning_decision_service)],
    information: Annotated[PlanningInformationService, Depends(get_planning_information_service)],
) -> RecommendationResponse:
    try:
        plan = await service.get_plan(current_user.id, plan_id)
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc

    criteria = criteria_from_plan(plan)
    result = await decision.recommend(criteria)
    return RecommendationResponse(
        data_source=result.source,
        is_live=result.is_live,
        attribution=result.attribution,
        freshness=result.freshness,
        candidates=[DecisionCandidateRead.from_candidate(candidate) for candidate in result.candidates],
    )


@router.patch("/plans/{plan_id}", response_model=PlanRead)
async def update_plan(plan_id: UUID, body: PlanPatchRequest, current_user: Annotated[User, Depends(get_current_user)],
                      service: Annotated[PlanningService, Depends(get_planning_service)]) -> PlanRead:
    try:
        return PlanRead.from_plan(await service.update_plan(current_user.id, plan_id, body.to_changes()))
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: UUID, current_user: Annotated[User, Depends(get_current_user)],
                      service: Annotated[PlanningService, Depends(get_planning_service)]) -> Response:
    try:
        await service.delete_plan(current_user.id, plan_id)
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/plans/{plan_id}/items", response_model=PlanItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(plan_id: UUID, body: PlanItemCreateRequest, current_user: Annotated[User, Depends(get_current_user)],
                      service: Annotated[PlanningService, Depends(get_planning_service)]) -> PlanItemRead:
    try:
        return PlanItemRead.from_item(await service.create_item(current_user.id, plan_id, body.to_data()))
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/items/from-option", response_model=PlanItemRead, status_code=status.HTTP_201_CREATED)
async def select_option(plan_id: UUID, body: SelectOptionRequest,
                        current_user: Annotated[User, Depends(get_current_user)],
                        service: Annotated[PlanSelectionService, Depends(get_plan_selection_service)]) -> PlanItemRead:
    try:
        item = await service.select_option(current_user.id, plan_id, body.option_id, body.option_type,
                                           position=body.position, start_time=body.start_time, end_time=body.end_time)
        return PlanItemRead.from_item(item)
    except (PlanningNotFoundError, OptionNotFoundError) as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/plans/{plan_id}/items", response_model=list[PlanItemRead])
async def list_items(plan_id: UUID, current_user: Annotated[User, Depends(get_current_user)],
                     service: Annotated[PlanningService, Depends(get_planning_service)]) -> list[PlanItemRead]:
    try:
        return [PlanItemRead.from_item(item) for item in await service.list_items(current_user.id, plan_id)]
    except PlanningNotFoundError as exc:
        raise _not_found(exc) from exc


@router.patch("/plans/{plan_id}/items/{item_id}", response_model=PlanItemRead)
async def update_item(plan_id: UUID, item_id: UUID, body: PlanItemPatchRequest,
                      current_user: Annotated[User, Depends(get_current_user)],
                      service: Annotated[PlanningService, Depends(get_planning_service)]) -> PlanItemRead:
    try:
        return PlanItemRead.from_item(await service.update_item(current_user.id, plan_id, item_id, body.to_changes()))
    except (PlanningNotFoundError, PlanItemNotFoundError) as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/plans/{plan_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(plan_id: UUID, item_id: UUID, current_user: Annotated[User, Depends(get_current_user)],
                      service: Annotated[PlanningService, Depends(get_planning_service)]) -> Response:
    try:
        await service.delete_item(current_user.id, plan_id, item_id)
    except (PlanningNotFoundError, PlanItemNotFoundError) as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
