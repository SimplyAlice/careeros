from datetime import UTC, datetime, timedelta
from uuid import uuid4
import pytest

from app.application.mobility.integration import (
    CrowdReportValidator,
    build_mobility_requirement_between_items,
    mobility_evidence_to_live_signal,
)
from app.domain.entities.mobility.enums import MobilitySourceType
from app.domain.entities.mobility.models import MobilityEvidence
from app.domain.entities.planning.live_intelligence import LiveChangeType, LiveSignalType
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


def test_build_mobility_requirement_between_items():
    plan_id = uuid4()
    item_a = PlanItem(
        plan_id=plan_id,
        name="Lunch at Kloof Street House",
        item_type=PlanItemType.FOOD,
        location="Kloof Street",
        end_time=datetime(2026, 9, 25, 14, 0, tzinfo=UTC),
    )
    item_b = PlanItem(
        plan_id=plan_id,
        name="Zeitz MOCAA",
        item_type=PlanItemType.ACTIVITY,
        location="V&A Waterfront",
        start_time=datetime(2026, 9, 25, 14, 45, tzinfo=UTC),
    )

    req = build_mobility_requirement_between_items(item_a, item_b, party_size=2)
    assert req is not None
    assert req.origin == "Kloof Street"
    assert req.destination == "V&A Waterfront"
    assert req.departure_time == datetime(2026, 9, 25, 14, 0, tzinfo=UTC)
    assert req.arrival_time == datetime(2026, 9, 25, 14, 45, tzinfo=UTC)
    assert req.party_size == 2


def test_build_mobility_requirement_same_or_empty_location():
    plan_id = uuid4()
    item_a = PlanItem(
        plan_id=plan_id,
        name="Lunch",
        item_type=PlanItemType.FOOD,
        location="Waterfront",
    )
    item_b = PlanItem(
        plan_id=plan_id,
        name="Drinks",
        item_type=PlanItemType.FOOD,
        location="Waterfront",
    )
    item_no_loc = PlanItem(
        plan_id=plan_id,
        name="Walk around",
        item_type=PlanItemType.ACTIVITY,
        location=None,
    )

    assert build_mobility_requirement_between_items(item_a, item_b) is None
    assert build_mobility_requirement_between_items(item_a, item_no_loc) is None


def test_mobility_evidence_to_live_signal():
    now = datetime.now(UTC)
    ev = MobilityEvidence(
        claim="MyCiTi Route 101 delayed 15 minutes due to roadworks",
        source="MyCiTi Dispatch Advisory",
        source_type=MobilitySourceType.OFFICIAL_REALTIME,
        observed_at=now,
        confidence=0.9,
        relevant_provider="myciti",
    )

    signal = mobility_evidence_to_live_signal(
        evidence=ev,
        target_name="MyCiTi Bus 101",
        is_disruption=True,
    )

    assert signal.signal_type == LiveSignalType.AVAILABILITY
    assert signal.change_type == LiveChangeType.EVENT_RESCHEDULED
    assert signal.is_meaningful_change is True
    assert signal.message == ev.claim


def test_crowd_report_validation():
    # Invalid short claim
    with pytest.raises(ValueError, match="at least 5 characters"):
        CrowdReportValidator.validate_and_create_evidence("bad", "myciti")

    # Valid report
    crowd_ev = CrowdReportValidator.validate_and_create_evidence(
        claim="Bus did not arrive at Queens Beach stop",
        provider="myciti",
        route_or_stop="104",
        corroboration_count=1,
    )
    assert crowd_ev.source_type == MobilitySourceType.CROWD_REPORT
    assert crowd_ev.confidence == 0.35
    assert not crowd_ev.is_expired

    # Corroborated report has higher confidence
    corroborated_ev = CrowdReportValidator.validate_and_create_evidence(
        claim="Bus did not arrive at Queens Beach stop",
        provider="myciti",
        route_or_stop="104",
        corroboration_count=3,
    )
    assert corroborated_ev.confidence == 0.55

    # Cannot override non-expired official timetable
    official_ev = MobilityEvidence(
        claim="Scheduled service on time",
        source="Official Timetable",
        source_type=MobilitySourceType.OFFICIAL_TIMETABLE,
        observed_at=datetime.now(UTC),
        confidence=0.85,
    )
    assert CrowdReportValidator.can_override_official(corroborated_ev, official_ev) is False
