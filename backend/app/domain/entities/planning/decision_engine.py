"""Deterministic planning decision engine.

Given a set of provider-neutral options and a `DecisionCriteria`, this
module produces explainable `DecisionCandidate`s with a transparent,
purely additive integer score. It contains no ML, no randomness, and no
I/O: the same inputs always yield the same ordered output.
"""
from __future__ import annotations

from decimal import Decimal

from app.domain.entities.planning.decision import (
    CandidateType,
    DecisionCandidate,
    DecisionCriteria,
    DecisionReason,
    DecisionResult,
    ReasonOutcome,
    ReasonType,
)
from app.domain.entities.planning.information import Activity, InformationCategory, Place

# Transparent, additive weights. They tally preference fit, not confidence.
CATEGORY_MATCH_SCORE = 40
BUDGET_FIT_SCORE = 25
GROUP_FIT_SCORE = 15
LOCATION_MATCH_SCORE = 10
DURATION_FIT_SCORE = 10
PLACE_DURATION_NEUTRAL_SCORE = 5


def decide(
    criteria: DecisionCriteria,
    places: list[Place],
    activities: list[Activity],
) -> DecisionResult:
    """Evaluate all options and return them ordered best-first."""
    candidates = [
        evaluate_place(place, criteria) for place in places
    ] + [
        evaluate_activity(activity, criteria) for activity in activities
    ]
    # Eligible candidates first, then by descending score, then a stable,
    # deterministic tiebreak on option type and name (never input order).
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            not candidate.is_eligible,
            -candidate.score,
            candidate.option_type.value,
            candidate.name,
        ),
    )
    source = candidates[0].source if candidates else "unknown"
    return DecisionResult(candidates=tuple(ordered), source=source)


def evaluate_place(place: Place, criteria: DecisionCriteria) -> DecisionCandidate:
    reasons: list[DecisionReason] = []
    eligible = True
    eligible &= _assess_location(place.location, criteria.location, reasons)
    eligible &= _assess_category(place.category, criteria.category, reasons)
    eligible &= _assess_budget(place.price_from, criteria.maximum_cost, reasons)
    eligible &= _assess_group(
        place.minimum_group_size, place.maximum_group_size, criteria.group_size, reasons
    )
    reasons = _ensure_reasons(reasons, "place")
    return DecisionCandidate(
        option_id=place.id,
        option_type=CandidateType.PLACE,
        name=place.name,
        is_eligible=eligible,
        score=_score(criteria, place.category, place.price_from, place.location, None),
        reasons=tuple(reasons),
        category=place.category,
        cost=place.price_from,
        duration_minutes=None,
        location=place.location,
        source=place.source,
    )


def evaluate_activity(activity: Activity, criteria: DecisionCriteria) -> DecisionCandidate:
    reasons: list[DecisionReason] = []
    eligible = True
    eligible &= _assess_location(activity.location, criteria.location, reasons)
    eligible &= _assess_category(activity.category, criteria.category, reasons)
    eligible &= _assess_budget(activity.cost, criteria.maximum_cost, reasons)
    eligible &= _assess_group(
        activity.minimum_group_size, activity.maximum_group_size, criteria.group_size, reasons
    )
    eligible &= _assess_duration(
        activity.duration_minutes, criteria.maximum_duration_minutes, reasons
    )
    reasons = _ensure_reasons(reasons, "activity")
    return DecisionCandidate(
        option_id=activity.id,
        option_type=CandidateType.ACTIVITY,
        name=activity.name,
        is_eligible=eligible,
        score=_score(
            criteria, activity.category, activity.cost, activity.location, activity.duration_minutes
        ),
        reasons=tuple(reasons),
        category=activity.category,
        cost=activity.cost,
        duration_minutes=activity.duration_minutes,
        location=activity.location,
        source=activity.source,
    )


def _ensure_reasons(reasons: list[DecisionReason], kind: str) -> list[DecisionReason]:
    """Guarantee at least one reason so every candidate stays explainable.

    When no criteria were supplied, no constraint reason is emitted; a
    neutral general note keeps the candidate self-describing instead of
    silently carrying an empty explanation.
    """
    if not reasons:
        reasons.append(
            DecisionReason(
                ReasonType.GENERAL,
                ReasonOutcome.NEUTRAL,
                f"An available {kind} with no specific criteria to compare against",
            )
        )
    return reasons


def _assess_location(
    value: str | None, requested: str | None, reasons: list[DecisionReason]
) -> bool:
    if requested is None:
        return True
    if value is not None and value.casefold() == requested.strip().casefold():
        reasons.append(
            DecisionReason(ReasonType.LOCATION, ReasonOutcome.SUPPORTED, f"Fits the {value} location")
        )
    else:
        reasons.append(
            DecisionReason(
                ReasonType.LOCATION,
                ReasonOutcome.NEUTRAL,
                "Location was not specified for this option",
            )
        )
    return True


def _assess_category(
    value: InformationCategory,
    requested: InformationCategory | None,
    reasons: list[DecisionReason],
) -> bool:
    if requested is None:
        return True
    if value is requested:
        reasons.append(
            DecisionReason(
                ReasonType.CATEGORY,
                ReasonOutcome.SUPPORTED,
                f"Matches the requested {value.value} category",
            )
        )
    else:
        reasons.append(
            DecisionReason(
                ReasonType.CATEGORY,
                ReasonOutcome.NEUTRAL,
                f"Category {value.value} differs from the requested category",
            )
        )
    return True


def _assess_budget(
    cost: Decimal | None, maximum: Decimal | None, reasons: list[DecisionReason]
) -> bool:
    if maximum is None:
        return True
    if cost is None:
        reasons.append(
            DecisionReason(
                ReasonType.BUDGET,
                ReasonOutcome.NEUTRAL,
                "Cost is unknown, so it cannot be checked against the budget",
            )
        )
        return True
    if cost <= maximum:
        reasons.append(
            DecisionReason(
                ReasonType.BUDGET,
                ReasonOutcome.SUPPORTED,
                f"Cost of R{cost} is within the R{maximum} maximum budget",
            )
        )
        return True
    reasons.append(
        DecisionReason(
            ReasonType.BUDGET,
            ReasonOutcome.VIOLATED,
            f"Cost of R{cost} exceeds the R{maximum} maximum budget",
        )
    )
    return False


def _assess_group(
    minimum: int, maximum: int | None, group_size: int | None, reasons: list[DecisionReason]
) -> bool:
    if group_size is None:
        return True
    if group_size < minimum:
        reasons.append(
            DecisionReason(
                ReasonType.GROUP_SIZE,
                ReasonOutcome.VIOLATED,
                f"Requires at least {minimum} people; a group of {group_size} is too small",
            )
        )
        return False
    if maximum is not None and group_size > maximum:
        reasons.append(
            DecisionReason(
                ReasonType.GROUP_SIZE,
                ReasonOutcome.VIOLATED,
                f"Supports groups of up to {maximum}; a group of {group_size} is too large",
            )
        )
        return False
    if maximum is None:
        message = f"Suitable for a group of {group_size} with no listed maximum"
    else:
        message = f"Supports groups of up to {maximum}"
    reasons.append(DecisionReason(ReasonType.GROUP_SIZE, ReasonOutcome.SUPPORTED, message))
    return True


def _assess_duration(
    duration_minutes: int | None, maximum: int | None, reasons: list[DecisionReason]
) -> bool:
    if maximum is None or duration_minutes is None:
        return True
    if duration_minutes <= maximum:
        reasons.append(
            DecisionReason(
                ReasonType.DURATION,
                ReasonOutcome.SUPPORTED,
                f"Duration of {duration_minutes} minutes fits the {maximum}-minute maximum",
            )
        )
        return True
    reasons.append(
        DecisionReason(
            ReasonType.DURATION,
            ReasonOutcome.VIOLATED,
            f"Duration of {duration_minutes} minutes exceeds the {maximum}-minute maximum",
        )
    )
    return False


def _score(
    criteria: DecisionCriteria,
    category: InformationCategory,
    cost: Decimal | None,
    location: str | None,
    duration_minutes: int | None,
) -> int:
    score = 0
    if criteria.category is not None and category is criteria.category:
        score += CATEGORY_MATCH_SCORE
    if criteria.maximum_cost is not None and (cost is None or cost <= criteria.maximum_cost):
        score += BUDGET_FIT_SCORE
    if criteria.group_size is not None:
        score += GROUP_FIT_SCORE
    if (
        criteria.location is not None
        and location is not None
        and location.casefold() == criteria.location.strip().casefold()
    ):
        score += LOCATION_MATCH_SCORE
    if criteria.maximum_duration_minutes is not None:
        if duration_minutes is None:
            score += PLACE_DURATION_NEUTRAL_SCORE
        elif duration_minutes <= criteria.maximum_duration_minutes:
            score += DURATION_FIT_SCORE
    return score
