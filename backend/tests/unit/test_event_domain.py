from uuid import uuid4

import pytest

from app.domain.entities.event import Event, EventSeverity, EventType


def test_event_can_be_created():
    event = Event(
        id=uuid4(),
        service_id=uuid4(),
        event_type=EventType.ERROR,
        severity=EventSeverity.CRITICAL,
        message="Payment API returned HTTP 500.",
    )

    assert event.event_type == EventType.ERROR
    assert event.severity == EventSeverity.CRITICAL
    assert event.message == "Payment API returned HTTP 500."


def test_event_requires_service_id():
    service_id = uuid4()

    event = Event(
        id=uuid4(),
        service_id=service_id,
        event_type=EventType.ALERT,
        severity=EventSeverity.WARNING,
        message="CPU usage exceeded threshold.",
    )

    assert event.service_id == service_id


def test_event_rejects_empty_message():
    with pytest.raises(ValueError, match="Event message cannot be empty"):
        Event(
            id=uuid4(),
            service_id=uuid4(),
            event_type=EventType.ERROR,
            severity=EventSeverity.ERROR,
            message="",
        )


def test_event_rejects_whitespace_message():
    with pytest.raises(ValueError, match="Event message cannot be empty"):
        Event(
            id=uuid4(),
            service_id=uuid4(),
            event_type=EventType.SYSTEM,
            severity=EventSeverity.INFO,
            message="   ",
        )