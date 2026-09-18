from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_operations_service
from app.application.operations.operations_service import OperationsService
from app.domain.entities.action import ActionStatus, ActionType
from app.domain.entities.approval import ApprovalStatus
from app.domain.entities.audit_log import AuditAction
from app.domain.entities.event import EventSeverity, EventType
from app.domain.entities.incident import IncidentSeverity, IncidentStatus

router = APIRouter(tags=["operations"])


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    service_id: UUID
    event_type: EventType
    severity: EventSeverity
    message: str
    incident_id: UUID | None
    evaluation_reason: str | None


class EventCreate(BaseModel):
    service_id: UUID
    event_type: EventType
    severity: EventSeverity
    message: str = Field(..., min_length=1, max_length=1000)


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    service_id: UUID
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    detection_reason: str | None


class IncidentCreate(BaseModel):
    service_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN


class ActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    service_id: UUID
    action_type: ActionType
    reason: str
    status: ActionStatus


class ActionCreate(BaseModel):
    service_id: UUID
    action_type: ActionType
    reason: str = Field(..., min_length=1, max_length=1000)
    status: ActionStatus = ActionStatus.PENDING


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action_id: UUID
    status: ApprovalStatus


class ApprovalCreate(BaseModel):
    action_id: UUID
    status: ApprovalStatus = ApprovalStatus.PENDING


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action_id: UUID
    action: AuditAction
    message: str


class AuditLogCreate(BaseModel):
    action_id: UUID
    action: AuditAction
    message: str = Field(..., min_length=1, max_length=1000)


@router.get("/events", response_model=list[EventRead])
async def list_events(service: Annotated[OperationsService, Depends(get_operations_service)]) -> list[EventRead]:
    return [EventRead.model_validate(item) for item in await service.list_events()]


@router.post("/events", response_model=EventRead, status_code=201)
async def create_event(body: EventCreate, service: Annotated[OperationsService, Depends(get_operations_service)]) -> EventRead:
    return EventRead.model_validate(await service.create_event(**body.model_dump()))


@router.get("/incidents", response_model=list[IncidentRead])
async def list_incidents(service: Annotated[OperationsService, Depends(get_operations_service)]) -> list[IncidentRead]:
    return [IncidentRead.model_validate(item) for item in await service.list_incidents()]


@router.post("/incidents", response_model=IncidentRead, status_code=201)
async def create_incident(body: IncidentCreate, service: Annotated[OperationsService, Depends(get_operations_service)]) -> IncidentRead:
    return IncidentRead.model_validate(await service.create_incident(**body.model_dump()))


@router.get("/actions", response_model=list[ActionRead])
async def list_actions(service: Annotated[OperationsService, Depends(get_operations_service)]) -> list[ActionRead]:
    return [ActionRead.model_validate(item) for item in await service.list_actions()]


@router.post("/actions", response_model=ActionRead, status_code=201)
async def create_action(body: ActionCreate, service: Annotated[OperationsService, Depends(get_operations_service)]) -> ActionRead:
    return ActionRead.model_validate(await service.create_action(**body.model_dump()))


@router.get("/approvals", response_model=list[ApprovalRead])
async def list_approvals(service: Annotated[OperationsService, Depends(get_operations_service)]) -> list[ApprovalRead]:
    return [ApprovalRead.model_validate(item) for item in await service.list_approvals()]


@router.post("/approvals", response_model=ApprovalRead, status_code=201)
async def create_approval(body: ApprovalCreate, service: Annotated[OperationsService, Depends(get_operations_service)]) -> ApprovalRead:
    return ApprovalRead.model_validate(await service.create_approval(**body.model_dump()))


@router.get("/audit-logs", response_model=list[AuditLogRead])
async def list_audit_logs(service: Annotated[OperationsService, Depends(get_operations_service)]) -> list[AuditLogRead]:
    return [AuditLogRead.model_validate(item) for item in await service.list_audit_logs()]


@router.post("/audit-logs", response_model=AuditLogRead, status_code=201)
async def create_audit_log(body: AuditLogCreate, service: Annotated[OperationsService, Depends(get_operations_service)]) -> AuditLogRead:
    return AuditLogRead.model_validate(await service.create_audit_log(**body.model_dump()))
