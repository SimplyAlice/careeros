from uuid import uuid4

import pytest

from app.application.operations.event_intelligence import DeterministicEventEvaluator
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import IncidentSeverity


@pytest.mark.parametrize(
    ("event_type", "severity", "expected_severity", "reason"),
    [
        (EventType.SYSTEM, EventSeverity.CRITICAL, IncidentSeverity.CRITICAL, "critical event severity"),
        (EventType.SYSTEM, EventSeverity.ERROR, IncidentSeverity.HIGH, "error event severity"),
        (EventType.ERROR, EventSeverity.INFO, IncidentSeverity.MEDIUM, "error event type"),
        (EventType.ALERT, EventSeverity.WARNING, IncidentSeverity.MEDIUM, "alert event type"),
    ],
)
def test_problematic_event_rules(
    event_type: EventType,
    severity: EventSeverity,
    expected_severity: IncidentSeverity,
    reason: str,
) -> None:
    decision = DeterministicEventEvaluator().evaluate(
        Event(uuid4(), uuid4(), event_type, severity, "Operational signal")
    )

    assert decision.problematic is True
    assert decision.incident_severity == expected_severity
    assert decision.reason == reason


@pytest.mark.parametrize(
    ("event_type", "severity"),
    [(EventType.HEALTH_CHECK, EventSeverity.WARNING), (EventType.DEPLOYMENT, EventSeverity.INFO)],
)
def test_non_problematic_event_rules(event_type: EventType, severity: EventSeverity) -> None:
    decision = DeterministicEventEvaluator().evaluate(Event(uuid4(), uuid4(), event_type, severity, "Routine signal"))

    assert decision.problematic is False
    assert decision.incident_severity is None
    assert decision.reason == "event does not meet incident detection rules"
