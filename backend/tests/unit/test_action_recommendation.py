from uuid import uuid4

import pytest

from app.application.operations.action_recommendation import ActionRecommendationService
from app.application.operations.incident_investigation import IncidentInvestigation, InvestigationEvent
from app.domain.entities.action import ActionType
from app.domain.entities.event import Event, EventSeverity, EventType
from app.domain.entities.incident import Incident, IncidentSeverity, IncidentStatus
from app.domain.entities.service import Service, ServiceStatus


class FakeInvestigationService:
    def __init__(self, result: IncidentInvestigation) -> None:
        self.result = result

    async def investigate(self, *, incident_id):
        return self.result


def _investigation(
    *,
    incident_severity: IncidentSeverity,
    incident_status: IncidentStatus,
    service_status: ServiceStatus,
    events: list[Event],
) -> IncidentInvestigation:
    service_id = uuid4()
    incident = Incident(uuid4(), service_id, "Payment API incident", incident_severity, incident_status)
    service = Service(service_id, "payments-api", "production", service_status)
    return IncidentInvestigation(
        incident=incident,
        service=service,
        events=[InvestigationEvent(event, index) for index, event in enumerate(events, 1)],
        findings=[],
    )


async def _recommend(investigation: IncidentInvestigation):
    return await ActionRecommendationService(FakeInvestigationService(investigation)).recommend(
        incident_id=investigation.incident.id
    )


@pytest.mark.asyncio
async def test_critical_degraded_service_recommends_restart() -> None:
    investigation = _investigation(
        incident_severity=IncidentSeverity.CRITICAL,
        incident_status=IncidentStatus.OPEN,
        service_status=ServiceStatus.DEGRADED,
        events=[Event(uuid4(), uuid4(), EventType.ERROR, EventSeverity.CRITICAL, "failure")],
    )

    result = await _recommend(investigation)

    assert result.recommendation is not None
    assert result.recommendation.action_type == ActionType.RESTART_SERVICE
    assert result.recommendation.requires_approval is True
    assert result.recommendation.confidence == "deterministic"


@pytest.mark.asyncio
async def test_critical_down_service_recommends_restart() -> None:
    investigation = _investigation(
        incident_severity=IncidentSeverity.CRITICAL,
        incident_status=IncidentStatus.OPEN,
        service_status=ServiceStatus.DOWN,
        events=[Event(uuid4(), uuid4(), EventType.SYSTEM, EventSeverity.CRITICAL, "failure")],
    )

    result = await _recommend(investigation)

    assert result.recommendation is not None
    assert result.recommendation.action_type == ActionType.RESTART_SERVICE


@pytest.mark.asyncio
async def test_high_incident_with_deployment_recommends_rollback() -> None:
    investigation = _investigation(
        incident_severity=IncidentSeverity.HIGH,
        incident_status=IncidentStatus.INVESTIGATING,
        service_status=ServiceStatus.HEALTHY,
        events=[Event(uuid4(), uuid4(), EventType.DEPLOYMENT, EventSeverity.ERROR, "deployment signal")],
    )

    result = await _recommend(investigation)

    assert result.recommendation is not None
    assert result.recommendation.action_type == ActionType.ROLLBACK_DEPLOYMENT


@pytest.mark.asyncio
async def test_open_error_signal_falls_back_to_acknowledge() -> None:
    investigation = _investigation(
        incident_severity=IncidentSeverity.MEDIUM,
        incident_status=IncidentStatus.OPEN,
        service_status=ServiceStatus.HEALTHY,
        events=[Event(uuid4(), uuid4(), EventType.ALERT, EventSeverity.WARNING, "alert signal")],
    )

    result = await _recommend(investigation)

    assert result.recommendation is not None
    assert result.recommendation.action_type == ActionType.ACKNOWLEDGE_INCIDENT


@pytest.mark.asyncio
async def test_resolved_incident_without_matching_rule_has_no_recommendation() -> None:
    investigation = _investigation(
        incident_severity=IncidentSeverity.LOW,
        incident_status=IncidentStatus.RESOLVED,
        service_status=ServiceStatus.HEALTHY,
        events=[],
    )

    result = await _recommend(investigation)

    assert result.recommendation is None
