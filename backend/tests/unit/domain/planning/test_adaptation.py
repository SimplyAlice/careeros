from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.planning.adaptation import (
    ChangeType,
    ItemAction,
    ItemDiff,
    PlanAdaptation,
)
from app.domain.entities.planning.decision import CandidateType
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType


def test_change_types_and_item_actions() -> None:
    assert ChangeType.TIME_SHIFT.value == "time_shift"
    assert ChangeType.BUDGET_REDUCED.value == "budget_reduced"
    assert ChangeType.VENUE_INVALIDATED.value == "venue_invalidated"
    assert ChangeType.EXCLUSION_ADDED.value == "exclusion_added"
    assert ChangeType.LOCATION_CHANGED.value == "location_changed"

    assert ItemAction.KEPT.value == "kept"
    assert ItemAction.REPLACED.value == "replaced"
    assert ItemAction.REMOVED.value == "removed"
    assert ItemAction.RESCHEDULED.value == "rescheduled"
    assert ItemAction.ADDED.value == "added"


def test_item_diff_creation() -> None:
    orig_id = uuid4()
    diff = ItemDiff(
        action=ItemAction.REPLACED,
        original_item_id=orig_id,
        original_name="Truth Coffee",
        new_name="Honest Chocolate",
        original_start_time=datetime(2026, 9, 26, 10, 0),
        new_start_time=datetime(2026, 9, 26, 14, 0),
        original_cost=Decimal("120"),
        new_cost=Decimal("90"),
        item_type=PlanItemType.FOOD,
        reason="Start time shifted to 14:00; Truth Coffee closed, replaced with Honest Chocolate",
        candidate_option_id=uuid4(),
        candidate_option_type=CandidateType.PLACE,
    )

    assert diff.action is ItemAction.REPLACED
    assert diff.original_name == "Truth Coffee"
    assert diff.new_name == "Honest Chocolate"
    assert diff.original_cost == Decimal("120")
    assert diff.new_cost == Decimal("90")


def test_plan_adaptation_defaults_and_summary() -> None:
    plan_id = uuid4()
    diff = ItemDiff(
        action=ItemAction.KEPT,
        original_name="Zeitz MOCAA",
        new_name="Zeitz MOCAA",
        reason="Preserved from original plan",
    )
    adaptation = PlanAdaptation(
        plan_id=plan_id,
        changes_detected=[ChangeType.TIME_SHIFT],
        narrative_summary="Plan adjusted: start shifted to 14:00; 1 stop kept.",
        diffs=[diff],
        new_total_cost=Decimal("250"),
        is_feasible=True,
    )

    assert adaptation.plan_id == plan_id
    assert adaptation.changes_detected == [ChangeType.TIME_SHIFT]
    assert len(adaptation.diffs) == 1
    assert adaptation.diffs[0].action is ItemAction.KEPT
    assert adaptation.is_feasible is True
    assert adaptation.feasibility_note is None
