from uuid import uuid4

import pytest

from app.domain.entities.incident import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


def test_incident_can_be_created():
    incident = Incident(
        id=uuid4(),
        service_id=uuid4(),
        title="Payment API is failing",
        severity=IncidentSeverity.HIGH,
    )

    assert incident.title == "Payment API is failing"
    assert incident.severity == IncidentSeverity.HIGH
    assert incident.status == IncidentStatus.OPEN


def test_incident_can_have_different_status():
    incident = Incident(
        id=uuid4(),
        service_id=uuid4(),
        title="Database latency detected",
        severity=IncidentSeverity.MEDIUM,
        status=IncidentStatus.INVESTIGATING,
    )

    assert incident.status == IncidentStatus.INVESTIGATING


def test_incident_requires_service_id():
    service_id = uuid4()

    incident = Incident(
        id=uuid4(),
        service_id=service_id,
        title="API health check failed",
        severity=IncidentSeverity.CRITICAL,
    )

    assert incident.service_id == service_id


def test_incident_rejects_empty_title():
    with pytest.raises(ValueError, match="Incident title cannot be empty"):
        Incident(
            id=uuid4(),
            service_id=uuid4(),
            title="",
            severity=IncidentSeverity.HIGH,
        )


def test_incident_rejects_whitespace_title():
    with pytest.raises(ValueError, match="Incident title cannot be empty"):
        Incident(
            id=uuid4(),
            service_id=uuid4(),
            title="   ",
            severity=IncidentSeverity.LOW,
        )