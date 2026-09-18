from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.operations.incident_investigation import (
    IncidentInvestigation,
    IncidentInvestigationService,
)
from app.domain.entities.action import ActionType
from app.domain.entities.event import EventSeverity, EventType
from app.domain.entities.incident import IncidentSeverity, IncidentStatus
from app.domain.entities.service import ServiceStatus


@dataclass(frozen=True)
class RecommendationEvidence:
    event_count: int
    critical_event_present: bool
    error_signal_present: bool
    deployment_event_present: bool
    service_status: ServiceStatus
    incident_severity: IncidentSeverity
    incident_status: IncidentStatus


@dataclass(frozen=True)
class ActionRecommendation:
    action_type: ActionType
    reason: str
    confidence: str = "deterministic"
    requires_approval: bool = True


@dataclass(frozen=True)
class IncidentActionRecommendation:
    incident_id: UUID
    service_id: UUID
    recommendation: ActionRecommendation | None
    evidence: RecommendationEvidence
    investigation_ordering_basis: str
    chronology_available: bool


class ActionRecommendationService:
    """Computes operator recommendations without persisting or executing actions."""

    def __init__(self, investigation: IncidentInvestigationService) -> None:
        self._investigation = investigation

    async def recommend(self, *, incident_id: UUID) -> IncidentActionRecommendation:
        investigation = await self._investigation.investigate(incident_id=incident_id)
        evidence = _evidence(investigation)
        recommendation = _recommend(investigation, evidence)
        return IncidentActionRecommendation(
            incident_id=investigation.incident.id,
            service_id=investigation.service.id,
            recommendation=recommendation,
            evidence=evidence,
            investigation_ordering_basis=investigation.ordering_basis,
            chronology_available=investigation.chronology_available,
        )


def _evidence(investigation: IncidentInvestigation) -> RecommendationEvidence:
    events = [item.event for item in investigation.events]
    return RecommendationEvidence(
        event_count=len(events),
        critical_event_present=any(event.severity == EventSeverity.CRITICAL for event in events),
        error_signal_present=any(event.event_type in (EventType.ERROR, EventType.ALERT) for event in events),
        deployment_event_present=any(event.event_type == EventType.DEPLOYMENT for event in events),
        service_status=investigation.service.status,
        incident_severity=investigation.incident.severity,
        incident_status=investigation.incident.status,
    )


def _recommend(
    investigation: IncidentInvestigation,
    evidence: RecommendationEvidence,
) -> ActionRecommendation | None:
    incident = investigation.incident
    service = investigation.service

    if (
        incident.severity == IncidentSeverity.CRITICAL
        and service.status in (ServiceStatus.DOWN, ServiceStatus.DEGRADED)
        and evidence.critical_event_present
    ):
        return ActionRecommendation(
            action_type=ActionType.RESTART_SERVICE,
            reason=(
                "The incident has critical severity, the affected service is "
                f"{service.status.value}, and a critical event is present."
            ),
        )

    if (
        incident.severity in (IncidentSeverity.HIGH, IncidentSeverity.CRITICAL)
        and evidence.deployment_event_present
    ):
        return ActionRecommendation(
            action_type=ActionType.ROLLBACK_DEPLOYMENT,
            reason=(
                "The incident has high or critical severity and the evidence "
                "contains a deployment event."
            ),
        )

    if incident.status in (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING) and evidence.error_signal_present:
        return ActionRecommendation(
            action_type=ActionType.ACKNOWLEDGE_INCIDENT,
            reason=(
                f"The incident is {incident.status.value} and the evidence "
                "contains an error or alert signal."
            ),
        )

    return None
