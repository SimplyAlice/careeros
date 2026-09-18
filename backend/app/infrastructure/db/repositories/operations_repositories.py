from __future__ import annotations

from builtins import list as builtins_list
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.action import Action, ActionStatus, ActionType
from app.domain.entities.approval import Approval, ApprovalStatus
from app.domain.entities.audit_log import AuditAction, AuditLog
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import Incident, IncidentSeverity, IncidentStatus
from app.infrastructure.db.models import ActionModel, ApprovalModel, AuditLogModel, EventModel, IncidentModel


class _Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


class SqlAlchemyEventRepository(_Repository):
    async def list(self) -> builtins_list[Event]:
        result = await self._session.execute(select(EventModel).order_by(EventModel.id))
        return [_event(row) for row in result.scalars().all()]

    async def list_for_incident(self, *, incident_id: UUID) -> builtins_list[Event]:
        stmt = select(EventModel).where(EventModel.incident_id == incident_id).order_by(EventModel.id)
        result = await self._session.execute(stmt)
        return [_event(row) for row in result.scalars().all()]

    async def create(self, event: Event) -> Event:
        row = EventModel(
            id=event.id,
            service_id=event.service_id,
            incident_id=event.incident_id,
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            evaluation_reason=event.evaluation_reason,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return _event(row)

    async def update(self, event: Event) -> Event:
        row = await self._session.get(EventModel, event.id)
        if row is None:
            raise ValueError(f"Event {event.id} was not found.")
        row.incident_id = event.incident_id
        row.evaluation_reason = event.evaluation_reason
        await self._session.flush()
        await self._session.commit()
        return _event(row)


class SqlAlchemyIncidentRepository(_Repository):
    async def list(self) -> builtins_list[Incident]:
        result = await self._session.execute(select(IncidentModel).order_by(IncidentModel.id))
        return [_incident(row) for row in result.scalars().all()]

    async def get_by_id(self, *, incident_id: UUID) -> Incident | None:
        row = await self._session.get(IncidentModel, incident_id)
        return _incident(row) if row is not None else None

    async def create(self, incident: Incident) -> Incident:
        row = IncidentModel(
            id=incident.id,
            service_id=incident.service_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            detection_reason=incident.detection_reason,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return _incident(row)

    async def get_active_for_service(self, *, service_id: UUID) -> Incident | None:
        stmt = select(IncidentModel).where(
            IncidentModel.service_id == service_id,
            IncidentModel.status.in_((IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)),
        ).order_by(IncidentModel.id)
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _incident(row) if row is not None else None

    async def update(self, incident: Incident) -> Incident:
        row = await self._session.get(IncidentModel, incident.id)
        if row is None:
            raise ValueError(f"Incident {incident.id} was not found.")
        row.severity = incident.severity
        row.status = incident.status
        row.detection_reason = incident.detection_reason
        await self._session.flush()
        await self._session.commit()
        return _incident(row)


class SqlAlchemyActionRepository(_Repository):
    async def list(self) -> builtins_list[Action]:
        result = await self._session.execute(select(ActionModel).order_by(ActionModel.id))
        return [_action(row) for row in result.scalars().all()]

    async def create(self, action: Action) -> Action:
        row = ActionModel(id=action.id, service_id=action.service_id, action_type=action.action_type, reason=action.reason, status=action.status)
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return _action(row)


class SqlAlchemyApprovalRepository(_Repository):
    async def list(self) -> builtins_list[Approval]:
        result = await self._session.execute(select(ApprovalModel).order_by(ApprovalModel.id))
        return [_approval(row) for row in result.scalars().all()]

    async def create(self, approval: Approval) -> Approval:
        row = ApprovalModel(id=approval.id, action_id=approval.action_id, status=approval.status)
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return _approval(row)


class SqlAlchemyAuditLogRepository(_Repository):
    async def list(self) -> builtins_list[AuditLog]:
        result = await self._session.execute(select(AuditLogModel).order_by(AuditLogModel.id))
        return [_audit_log(row) for row in result.scalars().all()]

    async def create(self, log: AuditLog) -> AuditLog:
        row = AuditLogModel(id=log.id, action_id=log.action_id, action=log.action, message=log.message)
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return _audit_log(row)


def _event(row: EventModel) -> Event:
    return Event(
        row.id,
        row.service_id,
        EventType(row.event_type),
        EventSeverity(row.severity),
        row.message,
        row.incident_id,
        row.evaluation_reason,
    )


def _incident(row: IncidentModel) -> Incident:
    return Incident(
        row.id,
        row.service_id,
        row.title,
        IncidentSeverity(row.severity),
        IncidentStatus(row.status),
        row.detection_reason,
    )


def _action(row: ActionModel) -> Action:
    return Action(row.id, row.service_id, ActionType(row.action_type), row.reason, ActionStatus(row.status))


def _approval(row: ApprovalModel) -> Approval:
    return Approval(row.id, row.action_id, ApprovalStatus(row.status))


def _audit_log(row: AuditLogModel) -> AuditLog:
    return AuditLog(row.id, row.action_id, AuditAction(row.action), row.message)
