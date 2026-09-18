from uuid import uuid4

import pytest

from app.application.operations.incident_investigation import IncidentInvestigationService
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import Incident, IncidentSeverity, IncidentStatus
from app.domain.entities.service import Service, ServiceStatus


class FakeIncidentRepository:
    def __init__(self, incident: Incident | None) -> None:
        self.incident = incident

    async def get_by_id(self, *, incident_id):
        return self.incident if self.incident and self.incident.id == incident_id else None


class FakeEventRepository:
    def __init__(self, events: list[Event]) -> None:
        self.events = events

    async def list_for_incident(self, *, incident_id):
        return sorted((event for event in self.events if event.incident_id == incident_id), key=lambda event: event.id)


class FakeServiceRepository:
    def __init__(self, service: Service) -> None:
        self.service = service

    async def get_by_id(self, *, service_id):
        return self.service if self.service.id == service_id else None


def _make_investigation(events: list[Event]) -> tuple[IncidentInvestigationService, Incident]:
    incident_id = uuid4()
    service_id = uuid4()
    incident = Incident(
        incident_id,
        service_id,
        "Payments API failure",
        IncidentSeverity.HIGH,
        IncidentStatus.OPEN,
        "error event severity",
    )
    service = Service(service_id, "payments-api", "production", ServiceStatus.DEGRADED)
    return (
        IncidentInvestigationService(
            incidents=FakeIncidentRepository(incident),
            events=FakeEventRepository(events),
            services=FakeServiceRepository(service),
        ),
        incident,
    )


def _make_incident() -> tuple[Incident, Service]:
    service_id = uuid4()
    return (
        Incident(uuid4(), service_id, "Payments API failure", IncidentSeverity.HIGH, IncidentStatus.OPEN, "error event severity"),
        Service(service_id, "payments-api", "production", ServiceStatus.DEGRADED),
    )


@pytest.mark.asyncio
async def test_investigation_reports_no_events_and_service_context() -> None:
    service, incident = _make_investigation([])

    result = await service.investigate(incident_id=incident.id)

    assert result.events == []
    assert result.service.name == "payments-api"
    assert "No associated event evidence is available." in result.findings
    assert "Incident detection reason is available." in result.findings


@pytest.mark.asyncio
async def test_investigation_reports_event_evidence_and_findings() -> None:
    incident, service_entity = _make_incident()
    events = [
        Event(uuid4(), incident.service_id, EventType.ALERT, EventSeverity.WARNING, "Latency alert.", incident.id),
        Event(uuid4(), incident.service_id, EventType.ERROR, EventSeverity.CRITICAL, "HTTP 500.", incident.id),
    ]
    service = IncidentInvestigationService(
        incidents=FakeIncidentRepository(incident),
        events=FakeEventRepository(events),
        services=FakeServiceRepository(service_entity),
    )

    result = await service.investigate(incident_id=incident.id)

    assert [item.sequence for item in result.events] == [1, 2]
    assert result.chronology_available is False
    assert "At least one event has critical severity." in result.findings
    assert "The event set contains an error or alert signal." in result.findings
    assert "The event set contains multiple severity levels." in result.findings


@pytest.mark.asyncio
async def test_investigation_reports_service_event_inconsistency() -> None:
    incident, service_entity = _make_incident()
    service = IncidentInvestigationService(
        incidents=FakeIncidentRepository(incident),
        events=FakeEventRepository(
            [Event(uuid4(), uuid4(), EventType.ERROR, EventSeverity.ERROR, "Other service.", incident_id=incident.id)]
        ),
        services=FakeServiceRepository(service_entity),
    )

    result = await service.investigate(incident_id=incident.id)

    assert "At least one associated event belongs to a different service." in result.findings


@pytest.mark.asyncio
async def test_investigation_unknown_incident_raises() -> None:
    service, incident = _make_investigation([])

    with pytest.raises(LookupError):
        await service.investigate(incident_id=uuid4())
