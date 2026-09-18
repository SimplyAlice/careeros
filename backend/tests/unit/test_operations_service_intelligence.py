from uuid import UUID, uuid4

import pytest

from app.application.operations.operations_service import OperationsService
from app.domain.entities.action import Action
from app.domain.entities.approval import Approval
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import Incident, IncidentSeverity


class FakeEventRepository:
    def __init__(self) -> None:
        self.items: list[Event] = []

    async def list(self) -> list[Event]:
        return self.items

    async def create(self, event: Event) -> Event:
        self.items.append(event)
        return event

    async def update(self, event: Event) -> Event:
        return event


class FakeIncidentRepository:
    def __init__(self) -> None:
        self.items: list[Incident] = []

    async def list(self) -> list[Incident]:
        return self.items

    async def create(self, incident: Incident) -> Incident:
        self.items.append(incident)
        return incident

    async def get_active_for_service(self, *, service_id: UUID) -> Incident | None:
        return next((item for item in self.items if item.service_id == service_id), None)

    async def update(self, incident: Incident) -> Incident:
        return incident


class FakeActionRepository:
    async def list(self) -> list[Action]:
        return []

    async def create(self, action: Action) -> Action:
        return action


class FakeApprovalRepository:
    async def list(self) -> list[Approval]:
        return []

    async def create(self, approval: Approval) -> Approval:
        return approval


class FakeAuditLogRepository:
    async def list(self) -> list[AuditLog]:
        return []

    async def create(self, log: AuditLog) -> AuditLog:
        return log


def _service() -> tuple[OperationsService, FakeEventRepository, FakeIncidentRepository, UUID]:
    events = FakeEventRepository()
    incidents = FakeIncidentRepository()
    service_id = uuid4()
    operations = OperationsService(
        events=events,
        incidents=incidents,
        actions=FakeActionRepository(),
        approvals=FakeApprovalRepository(),
        audit_logs=FakeAuditLogRepository(),
    )
    return operations, events, incidents, service_id


@pytest.mark.asyncio
async def test_problematic_event_creates_incident_and_stores_reasoning() -> None:
    operations, events, incidents, service_id = _service()

    created = await operations.create_event(
        service_id=service_id,
        event_type=EventType.ERROR,
        severity=EventSeverity.CRITICAL,
        message="Payments are failing.",
    )

    assert len(incidents.items) == 1
    assert created.incident_id == incidents.items[0].id
    assert created.evaluation_reason == "critical event severity"
    assert incidents.items[0].detection_reason == "critical event severity"
    assert events.items[0] is created


@pytest.mark.asyncio
async def test_second_problematic_event_reuses_and_escalates_incident() -> None:
    operations, _, incidents, service_id = _service()

    first = await operations.create_event(
        service_id=service_id,
        event_type=EventType.ALERT,
        severity=EventSeverity.WARNING,
        message="Latency alert.",
    )
    second = await operations.create_event(
        service_id=service_id,
        event_type=EventType.ERROR,
        severity=EventSeverity.CRITICAL,
        message="Requests are failing.",
    )

    assert len(incidents.items) == 1
    assert first.incident_id == second.incident_id == incidents.items[0].id
    assert incidents.items[0].severity == IncidentSeverity.CRITICAL


@pytest.mark.asyncio
async def test_non_problematic_event_does_not_create_incident() -> None:
    operations, _, incidents, service_id = _service()

    event = await operations.create_event(
        service_id=service_id,
        event_type=EventType.HEALTH_CHECK,
        severity=EventSeverity.WARNING,
        message="Health check passed with a warning.",
    )

    assert event.incident_id is None
    assert event.evaluation_reason == "event does not meet incident detection rules"
    assert incidents.items == []
