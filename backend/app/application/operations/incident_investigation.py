from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.operations.ports import EventRepository, IncidentRepository
from app.application.services.ports import ServiceRepository
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import Incident, IncidentSeverity
from app.domain.entities.service import Service


class IncidentNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class InvestigationEvent:
    event: Event
    sequence: int


@dataclass(frozen=True)
class IncidentInvestigation:
    incident: Incident
    service: Service
    events: list[InvestigationEvent]
    findings: list[str]
    ordering_basis: str = "event_id"
    chronology_available: bool = False


class IncidentInvestigationService:
    """Computes deterministic investigation evidence without persistence."""

    def __init__(
        self,
        *,
        incidents: IncidentRepository,
        events: EventRepository,
        services: ServiceRepository,
    ) -> None:
        self._incidents = incidents
        self._events = events
        self._services = services

    async def investigate(self, *, incident_id: UUID) -> IncidentInvestigation:
        incident = await self._incidents.get_by_id(incident_id=incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident {incident_id} was not found.")

        events = await self._events.list_for_incident(incident_id=incident_id)
        service = await self._services.get_by_id(service_id=incident.service_id)
        if service is None:
            raise LookupError(f"Service {incident.service_id} was not found.")

        sequenced_events = [InvestigationEvent(event=event, sequence=index) for index, event in enumerate(events, 1)]
        findings = _build_findings(incident=incident, service=service, events=events)
        return IncidentInvestigation(
            incident=incident,
            service=service,
            events=sequenced_events,
            findings=findings,
        )


def _build_findings(*, incident: Incident, service: Service, events: list[Event]) -> list[str]:
    findings = [
        f"Incident is associated with {len(events)} event{'s' if len(events) != 1 else ''}.",
    ]
    if not events:
        findings.append("No associated event evidence is available.")
    if any(event.severity == EventSeverity.CRITICAL for event in events):
        findings.append("At least one event has critical severity.")
    if any(event.severity == EventSeverity.ERROR for event in events):
        findings.append("At least one event has error severity.")
    if any(event.event_type in (EventType.ERROR, EventType.ALERT) for event in events):
        findings.append("The event set contains an error or alert signal.")
    if len({event.severity for event in events}) > 1:
        findings.append("The event set contains multiple severity levels.")
    if events and _severity_rank(max(events, key=lambda event: _severity_rank(event.severity)).severity) > _severity_rank(incident.severity):
        findings.append("The event set contains a severity higher than the incident severity.")
    if all(event.service_id == incident.service_id for event in events):
        findings.append("All associated events belong to the incident service.")
    else:
        findings.append("At least one associated event belongs to a different service.")
    findings.append(f"Incident detection reason is {'available' if incident.detection_reason else 'not available'}.")
    findings.append(f"Current service status is {service.status.value}.")
    return findings


def _severity_rank(severity: IncidentSeverity | EventSeverity) -> int:
    return {
        EventSeverity.INFO: 1,
        EventSeverity.WARNING: 2,
        EventSeverity.ERROR: 3,
        EventSeverity.CRITICAL: 4,
        IncidentSeverity.LOW: 1,
        IncidentSeverity.MEDIUM: 2,
        IncidentSeverity.HIGH: 3,
        IncidentSeverity.CRITICAL: 4,
    }[severity]
