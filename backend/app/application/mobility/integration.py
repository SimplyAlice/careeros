from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.domain.entities.mobility.enums import (
    MobilityLiveStatus,
    MobilitySourceType,
    get_source_hierarchy_weight,
)
from app.domain.entities.mobility.models import MobilityEvidence, MobilityRequirement
from app.domain.entities.planning.information import FreshnessKind
from app.domain.entities.planning.live_intelligence import (
    LiveChangeType,
    LiveSignal,
    LiveSignalType,
)
from app.domain.entities.planning.plan_item import PlanItem


def build_mobility_requirement_between_items(
    item_a: PlanItem,
    item_b: PlanItem,
    party_size: int = 1,
) -> MobilityRequirement | None:
    """Safely construct a MobilityRequirement between two sequential itinerary stops.

    If either item lacks a location or both locations are identical, returns None without error.
    """
    loc_a = item_a.location.strip() if item_a.location else None
    loc_b = item_b.location.strip() if item_b.location else None

    if not loc_a or not loc_b or loc_a.lower() == loc_b.lower():
        return None

    dep_time = item_a.end_time or item_a.start_time
    arr_time = item_b.start_time or item_b.end_time

    return MobilityRequirement(
        origin=loc_a,
        destination=loc_b,
        departure_time=dep_time,
        arrival_time=arr_time,
        date=dep_time.date() if dep_time else None,
        party_size=party_size,
    )


def mobility_evidence_to_live_signal(
    evidence: MobilityEvidence,
    target_name: str,
    target_item_id: UUID | None = None,
    is_disruption: bool = False,
) -> LiveSignal:
    """Bridge a MobilityEvidence record into Dayform M7's existing LiveSignal entity.

    Ensures transport updates flow naturally through the existing M7 -> M5 pipeline
    without creating a duplicate live intelligence system.
    """
    freshness = (
        FreshnessKind.LIVE
        if evidence.source_type == MobilitySourceType.OFFICIAL_REALTIME
        else FreshnessKind.RECENTLY_VERIFIED
    )

    change_type = (
        LiveChangeType.INFORMATIONAL if not is_disruption else LiveChangeType.EVENT_RESCHEDULED
    )

    return LiveSignal(
        source=evidence.source,
        signal_type=LiveSignalType.AVAILABILITY,
        observed_at=evidence.observed_at,
        freshness=freshness,
        target_name=target_name,
        target_item_id=target_item_id,
        change_type=change_type,
        current_value=evidence.claim,
        is_meaningful_change=is_disruption,
        message=evidence.claim,
    )


class CrowdReportValidator:
    """Validation and trust boundary for crowdsourced mobility feedback.

    Guarantees that unverified user reports cannot silently override official data.
    """

    DEFAULT_TTL_MINUTES = 45

    @classmethod
    def validate_and_create_evidence(
        cls,
        claim: str,
        provider: str,
        route_or_stop: str | None = None,
        reporter_id: str | None = None,
        corroboration_count: int = 1,
    ) -> MobilityEvidence:
        clean_claim = claim.strip()
        if len(clean_claim) < 5:
            raise ValueError("Crowdsourced report claim must be at least 5 characters.")

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=cls.DEFAULT_TTL_MINUTES)

        # Baseline crowd confidence is low; increases with corroborated reports but capped at 0.65
        base_confidence = 0.35
        boost = min(0.30, (corroboration_count - 1) * 0.10)
        confidence = round(base_confidence + boost, 2)

        return MobilityEvidence(
            claim=f"[User Report ({corroboration_count} report(s))] {clean_claim}",
            source=f"Community Mobility Feedback ({provider})",
            source_type=MobilitySourceType.CROWD_REPORT,
            observed_at=now,
            expires_at=expires_at,
            confidence=confidence,
            relevant_provider=provider,
            relevant_route_or_stop=route_or_stop,
        )

    @classmethod
    def can_override_official(
        cls, crowd_evidence: MobilityEvidence, official_evidence: MobilityEvidence
    ) -> bool:
        """Determines whether crowd evidence has sufficient corroboration to override official timetable facts.

        Always returns False under the hierarchy of trust unless official evidence is stale.
        """
        crowd_weight = get_source_hierarchy_weight(crowd_evidence.source_type)
        official_weight = get_source_hierarchy_weight(official_evidence.source_type)

        # If official evidence is not expired, it cannot be overridden by crowd reports
        if not official_evidence.is_expired:
            return False

        return crowd_weight > official_weight
