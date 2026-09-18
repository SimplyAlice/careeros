from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import IncidentSeverity


@dataclass(frozen=True)
class EventDecision:
    problematic: bool
    incident_severity: IncidentSeverity | None
    reason: str


class DeterministicEventEvaluator:
    """Classify operational Events using stable, explainable rules."""

    def evaluate(self, event: Event) -> EventDecision:
        if event.severity == EventSeverity.CRITICAL:
            return EventDecision(True, IncidentSeverity.CRITICAL, "critical event severity")
        if event.severity == EventSeverity.ERROR:
            return EventDecision(True, IncidentSeverity.HIGH, "error event severity")
        if event.event_type == EventType.ERROR:
            return EventDecision(True, IncidentSeverity.MEDIUM, "error event type")
        if event.event_type == EventType.ALERT:
            return EventDecision(True, IncidentSeverity.MEDIUM, "alert event type")
        return EventDecision(False, None, "event does not meet incident detection rules")
