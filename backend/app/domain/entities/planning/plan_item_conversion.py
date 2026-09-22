"""Converts a selected `DecisionCandidate` into a `PlanItem`.

Kept separate from the decision model so the conversion rules are easy to
find and test. This is a pure builder: it never persists anything. Callers
(application services) decide when a selection is actually saved.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.entities.planning.decision import DecisionCandidate
from app.domain.entities.planning.information import InformationCategory
from app.domain.entities.planning.plan_item import PlanItem, PlanItemType

_ITEM_TYPE_BY_CATEGORY = {
    InformationCategory.FOOD: PlanItemType.FOOD,
    InformationCategory.SHOPPING: PlanItemType.SHOPPING,
    InformationCategory.ENTERTAINMENT: PlanItemType.ACTIVITY,
    InformationCategory.CULTURE: PlanItemType.ACTIVITY,
    InformationCategory.NATURE: PlanItemType.ACTIVITY,
    InformationCategory.WELLNESS: PlanItemType.ACTIVITY,
}


def candidate_to_plan_item(
    candidate: DecisionCandidate,
    *,
    plan_id: UUID,
    position: int = 0,
    description: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> PlanItem:
    """Build (but never persist) a PlanItem from a selected candidate.

    Name, item type, cost and location come from authoritative candidate
    data. Optional description/timing/position come from the caller. No
    value is invented: anything unknown stays optional.
    """
    return PlanItem(
        plan_id=plan_id,
        name=candidate.name,
        item_type=_ITEM_TYPE_BY_CATEGORY.get(candidate.category, PlanItemType.OTHER),
        description=description,
        start_time=start_time,
        end_time=end_time,
        estimated_cost=candidate.cost,
        location=candidate.location,
        position=position,
    )
