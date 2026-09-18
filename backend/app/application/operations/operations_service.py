from __future__ import annotations

from uuid import UUID, uuid4

from app.application.operations.ports import (
    ActionRepository,
    ApprovalRepository,
    AuditLogRepository,
    EventRepository,
    IncidentRepository,
)
from app.domain.entities.action import Action, ActionStatus, ActionType
from app.domain.entities.approval import Approval, ApprovalStatus
from app.domain.entities.audit_log import AuditAction, AuditLog
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import Incident, IncidentSeverity, IncidentStatus


class OperationsService:
    """Application use cases for the first operational chain."""

    def __init__(
        self,
        *,
        events: EventRepository,
        incidents: IncidentRepository,
        actions: ActionRepository,
        approvals: ApprovalRepository,
        audit_logs: AuditLogRepository,
    ) -> None:
        self._events = events
        self._incidents = incidents
        self._actions = actions
        self._approvals = approvals
        self._audit_logs = audit_logs

    async def list_events(self) -> list[Event]:
        return await self._events.list()

    async def create_event(
        self, *, service_id: UUID, event_type: EventType, severity: EventSeverity, message: str
    ) -> Event:
        return await self._events.create(Event(uuid4(), service_id, event_type, severity, message))

    async def list_incidents(self) -> list[Incident]:
        return await self._incidents.list()

    async def create_incident(
        self, *, service_id: UUID, title: str, severity: IncidentSeverity, status: IncidentStatus = IncidentStatus.OPEN
    ) -> Incident:
        return await self._incidents.create(Incident(uuid4(), service_id, title, severity, status))

    async def list_actions(self) -> list[Action]:
        return await self._actions.list()

    async def create_action(
        self, *, service_id: UUID, action_type: ActionType, reason: str, status: ActionStatus = ActionStatus.PENDING
    ) -> Action:
        return await self._actions.create(Action(uuid4(), service_id, action_type, reason, status))

    async def list_approvals(self) -> list[Approval]:
        return await self._approvals.list()

    async def create_approval(
        self, *, action_id: UUID, status: ApprovalStatus = ApprovalStatus.PENDING
    ) -> Approval:
        return await self._approvals.create(Approval(uuid4(), action_id, status))

    async def list_audit_logs(self) -> list[AuditLog]:
        return await self._audit_logs.list()

    async def create_audit_log(self, *, action_id: UUID, action: AuditAction, message: str) -> AuditLog:
        return await self._audit_logs.create(AuditLog(uuid4(), action_id, action, message))
