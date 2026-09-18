from __future__ import annotations

from typing import Protocol

from app.domain.entities.action import Action
from app.domain.entities.approval import Approval
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.event import Event
from app.domain.entities.incident import Incident


class EventRepository(Protocol):
    async def list(self) -> list[Event]: ...
    async def create(self, event: Event) -> Event: ...


class IncidentRepository(Protocol):
    async def list(self) -> list[Incident]: ...
    async def create(self, incident: Incident) -> Incident: ...


class ActionRepository(Protocol):
    async def list(self) -> list[Action]: ...
    async def create(self, action: Action) -> Action: ...


class ApprovalRepository(Protocol):
    async def list(self) -> list[Approval]: ...
    async def create(self, approval: Approval) -> Approval: ...


class AuditLogRepository(Protocol):
    async def list(self) -> list[AuditLog]: ...
    async def create(self, log: AuditLog) -> AuditLog: ...
