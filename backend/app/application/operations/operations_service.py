from __future__ import annotations

from uuid import UUID, uuid4

from app.application.operations.event_intelligence import DeterministicEventEvaluator
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
        evaluator: DeterministicEventEvaluator | None = None,
    ) -> None:
        self._events = events
        self._incidents = incidents
        self._actions = actions
        self._approvals = approvals
        self._audit_logs = audit_logs
        self._evaluator = evaluator or DeterministicEventEvaluator()

    async def list_events(self) -> list[Event]:
        return await self._events.list()

    async def create_event(
        self, *, service_id: UUID, event_type: EventType, severity: EventSeverity, message: str
    ) -> Event:
        event = await self._events.create(Event(uuid4(), service_id, event_type, severity, message))
        decision = self._evaluator.evaluate(event)
        event.evaluation_reason = decision.reason

        if not decision.problematic:
            return await self._events.update(event)

        incident_severity = decision.incident_severity
        assert incident_severity is not None
        incident = await self._incidents.get_active_for_service(service_id=service_id)
        if incident is None:
            incident = await self._incidents.create(
                Incident(
                    id=uuid4(),
                    service_id=service_id,
                    title=f"Operational problem: {message}"[:255],
                    severity=incident_severity,
                    detection_reason=decision.reason,
                )
            )
        else:
            if _severity_rank(incident_severity) > _severity_rank(incident.severity):
                incident.severity = incident_severity
            incident.detection_reason = f"{incident.detection_reason}; {decision.reason}" if incident.detection_reason else decision.reason
            incident = await self._incidents.update(incident)

        event.incident_id = incident.id
        return await self._events.update(event)

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


def _severity_rank(severity: IncidentSeverity | None) -> int:
    if severity is None:
        return 0
    return {
        IncidentSeverity.LOW: 1,
        IncidentSeverity.MEDIUM: 2,
        IncidentSeverity.HIGH: 3,
        IncidentSeverity.CRITICAL: 4,
    }[severity]
