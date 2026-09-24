"""Deterministic planning decision engine.

Given a set of provider-neutral options and a `DecisionCriteria`, this
module produces explainable `DecisionCandidate`s with a transparent,
purely additive integer score. It contains no ML, no randomness, and no
I/O: the same inputs always yield the same ordered output.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
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
from app.domain.entities.planning.temporal import parse_opening_hours

# Transparent, additive weights. They tally preference fit, not confidence.
CATEGORY_MATCH_SCORE = 40
BUDGET_FIT_SCORE = 25
GROUP_FIT_SCORE = 15
LOCATION_MATCH_SCORE = 10
DURATION_FIT_SCORE = 10
PLACE_DURATION_NEUTRAL_SCORE = 5
PREFERENCE_FIT_SCORE = 15
OCCASION_FIT_SCORE = 15
ACTIVITY_TYPE_FIT_SCORE = 20
TEMPORAL_FIT_SCORE = 20
SEMANTIC_MATCH_SCORE = 15


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
    is_live = any(c.freshness == "live" for c in candidates)
    freshness = "live" if is_live else (candidates[0].freshness if candidates else "fixture")
    attribution = "© OpenStreetMap contributors" if any("openstreetmap" in (c.source or "").lower() for c in candidates) else None
    trade_off_summary = _generate_trade_off_summary(criteria, ordered)
    return DecisionResult(
        candidates=tuple(ordered),
        source=source,
        is_live=is_live,
        attribution=attribution,
        freshness=freshness,
        trade_off_summary=trade_off_summary,
    )


def evaluate_place(place: Place, criteria: DecisionCriteria) -> DecisionCandidate:
    reasons: list[DecisionReason] = []
    eligible = True
    eligible &= _assess_location(place.location, criteria.location, reasons, address=place.address)
    eligible &= _assess_category(place.category, criteria.category, reasons)
    eligible &= _assess_budget(place.price_from, criteria.maximum_cost, reasons)
    eligible &= _assess_group(
        place.minimum_group_size, place.maximum_group_size, criteria.group_size, reasons
    )
    eligible &= _assess_exclusions(
        place.category,
        place.name,
        place.description,
        place.price_from,
        dict(place.metadata),
        criteria.exclusions,
        reasons,
        setting_preference=criteria.setting_preference,
        weather_context=criteria.weather_context,
    )
    eligible &= _assess_opening_hours(
        place.name, place.opening_hours, criteria, reasons, duration_minutes=None
    )
    _assess_place_duration(criteria.duration_limit_minutes, reasons)
    desc_matched = _assess_semantic_descriptors(
        place.name, place.description, place.metadata, criteria.semantic_descriptors, reasons
    )
    pref_matched = _assess_preferences(
        place.category, place.description, criteria.preferences, reasons
    )
    occasion_matched = _assess_occasion(
        place.category, place.description, criteria.occasion, reasons
    )
    temporal_matched = any(
        r.type is ReasonType.OPENING_HOURS and r.outcome is ReasonOutcome.SUPPORTED for r in reasons
    )
    reasons = _ensure_reasons(reasons, "place")
    return DecisionCandidate(
        option_id=place.id,
        option_type=CandidateType.PLACE,
        name=place.name,
        is_eligible=eligible,
        score=_score(
            criteria,
            place.category,
            place.price_from,
            place.location,
            None,
            pref_matched=pref_matched,
            occasion_matched=occasion_matched,
            temporal_matched=temporal_matched,
            desc_matched=desc_matched,
        ),
        reasons=tuple(reasons),
        category=place.category,
        cost=place.price_from,
        duration_minutes=None,
        location=place.location,
        source=place.source,
        address=place.address,
        opening_hours=place.opening_hours,
        freshness=place.freshness,
        verified_at=place.verified_at,
        source_url=place.source_url,
        phone=place.phone,
        reservation_url=place.reservation_url,
    )


def evaluate_activity(activity: Activity, criteria: DecisionCriteria) -> DecisionCandidate:
    reasons: list[DecisionReason] = []
    eligible = True
    eligible &= _assess_location(activity.location, criteria.location, reasons, address=activity.address)
    eligible &= _assess_category(activity.category, criteria.category, reasons)
    eligible &= _assess_budget(activity.cost, criteria.maximum_cost, reasons)
    eligible &= _assess_group(
        activity.minimum_group_size, activity.maximum_group_size, criteria.group_size, reasons
    )
    eligible &= _assess_duration(
        activity.duration_minutes,
        criteria.maximum_duration_minutes,
        reasons,
        limit=criteria.duration_limit_minutes,
    )
    eligible &= _assess_exclusions(
        activity.category,
        activity.name,
        activity.description,
        activity.cost,
        dict(activity.metadata),
        criteria.exclusions,
        reasons,
        setting_preference=criteria.setting_preference,
        weather_context=criteria.weather_context,
    )
    act_hours = activity.metadata.get("opening_hours") if activity.metadata else None
    eligible &= _assess_opening_hours(
        activity.name, act_hours, criteria, reasons, duration_minutes=activity.duration_minutes
    )
    desc_matched = _assess_semantic_descriptors(
        activity.name, activity.description, activity.metadata, criteria.semantic_descriptors, reasons
    )
    pref_matched = _assess_preferences(
        activity.category, activity.description, criteria.preferences, reasons
    )
    occasion_matched = _assess_occasion(
        activity.category, activity.description, criteria.occasion, reasons
    )
    temporal_matched = any(
        r.type is ReasonType.OPENING_HOURS and r.outcome is ReasonOutcome.SUPPORTED for r in reasons
    )
    reasons = _ensure_reasons(reasons, "activity")
    return DecisionCandidate(
        option_id=activity.id,
        option_type=CandidateType.ACTIVITY,
        name=activity.name,
        is_eligible=eligible,
        score=_score(
            criteria,
            activity.category,
            activity.cost,
            activity.location,
            activity.duration_minutes,
            pref_matched=pref_matched,
            occasion_matched=occasion_matched,
            temporal_matched=temporal_matched,
            desc_matched=desc_matched,
        ),
        reasons=tuple(reasons),
        category=activity.category,
        cost=activity.cost,
        duration_minutes=activity.duration_minutes,
        location=activity.location,
        source=activity.source,
        address=activity.address,
        freshness=activity.freshness,
        verified_at=activity.verified_at,
        source_url=activity.source_url,
        phone=activity.phone,
        reservation_url=activity.reservation_url,
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
    value: str | None,
    requested: str | None,
    reasons: list[DecisionReason],
    address: str | None = None,
) -> bool:
    if requested is None:
        return True
    req_clean = requested.strip().casefold()
    val_clean = (value or "").strip().casefold()
    addr_clean = (address or "").strip().casefold()

    # 1. Exact match on city or location
    if val_clean and val_clean == req_clean:
        reasons.append(
            DecisionReason(ReasonType.LOCATION, ReasonOutcome.SUPPORTED, f"Fits the {value} location")
        )
        return True

    # 2. Neighborhood / address / substring match (e.g. "waterfront", "kloof", "camps bay", "gardens", "city bowl", "newlands")
    if req_clean in addr_clean or req_clean in val_clean or (val_clean in req_clean and len(val_clean) > 3):
        loc_display = address if address else value
        reasons.append(
            DecisionReason(
                ReasonType.LOCATION,
                ReasonOutcome.SUPPORTED,
                f"Located in {loc_display} which matches {requested}",
            )
        )
        return True

    # 3. If requested is general "around town", "town", "cape town", "in town"
    if req_clean in {"town", "around town", "cape town", "in town", "city"} and ("cape town" in val_clean or "cape town" in addr_clean):
        reasons.append(
            DecisionReason(
                ReasonType.LOCATION,
                ReasonOutcome.SUPPORTED,
                "Located in Cape Town, convenient for town outing",
            )
        )
        return True

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


def _assess_opening_hours(
    name: str,
    opening_hours: str | None,
    criteria: DecisionCriteria,
    reasons: list[DecisionReason],
    duration_minutes: int | None = None,
) -> bool:
    if criteria.day_of_week is None and criteria.start_time is None and criteria.time_window is None:
        return True

    if not opening_hours or not opening_hours.strip():
        reasons.append(
            DecisionReason(
                ReasonType.OPENING_HOURS,
                ReasonOutcome.NEUTRAL,
                "Opening hours could not be verified from official records. We recommend checking before visiting.",
            )
        )
        return True

    sched = parse_opening_hours(opening_hours)
    accommodate = sched.can_accommodate(
        criteria.day_of_week,
        criteria.start_time,
        duration_minutes=duration_minutes,
    )

    if accommodate is None:
        reasons.append(
            DecisionReason(
                ReasonType.OPENING_HOURS,
                ReasonOutcome.NEUTRAL,
                f"Opening hours ({opening_hours}) could not be fully verified for the requested time.",
            )
        )
        return True

    time_ctx = f" around {criteria.start_time}" if criteria.start_time else ""
    if criteria.day_of_week:
        day_val = criteria.day_of_week.value if hasattr(criteria.day_of_week, "value") else str(criteria.day_of_week)
        day_name = day_val.capitalize()
    else:
        day_name = None
    day_ctx = f"on {day_name}" if day_name else "for the requested window"

    if accommodate is False:
        reasons.append(
            DecisionReason(
                ReasonType.OPENING_HOURS,
                ReasonOutcome.VIOLATED,
                f"Closed {day_ctx}{time_ctx} (Hours: {opening_hours}).",
            )
        )
        return False

    reasons.append(
        DecisionReason(
            ReasonType.OPENING_HOURS,
            ReasonOutcome.SUPPORTED,
            f"Open {day_ctx}{time_ctx} ({opening_hours}).",
        )
    )
    return True



def _assess_place_duration(
    duration_limit_minutes: int | None,
    reasons: list[DecisionReason],
) -> None:
    if duration_limit_minutes is not None:
        reasons.append(
            DecisionReason(
                ReasonType.DURATION,
                ReasonOutcome.NEUTRAL,
                f"Visit duration for this venue is flexible and fits your {duration_limit_minutes}-minute window.",
            )
        )


def _assess_duration(
    duration_minutes: int | None,
    maximum: int | None,
    reasons: list[DecisionReason],
    limit: int | None = None,
) -> bool:
    cap = None
    if maximum is not None and limit is not None:
        cap = min(maximum, limit)
    elif maximum is not None:
        cap = maximum
    elif limit is not None:
        cap = limit

    if cap is None or duration_minutes is None:
        return True
    if duration_minutes <= cap:
        reasons.append(
            DecisionReason(
                ReasonType.DURATION,
                ReasonOutcome.SUPPORTED,
                f"Duration of {duration_minutes} minutes fits the {cap}-minute time limit",
            )
        )
        return True
    reasons.append(
        DecisionReason(
            ReasonType.DURATION,
            ReasonOutcome.VIOLATED,
            f"Duration of {duration_minutes} minutes exceeds the {cap}-minute time limit",
        )
    )
    return False


def _score(
    criteria: DecisionCriteria,
    category: InformationCategory,
    cost: Decimal | None,
    location: str | None,
    duration_minutes: int | None,
    pref_matched: bool = False,
    occasion_matched: bool = False,
    temporal_matched: bool = False,
    desc_matched: int = 0,
) -> int:
    score = 0
    if criteria.category is not None and category is criteria.category:
        score += CATEGORY_MATCH_SCORE
    if criteria.activity_types and category in criteria.activity_types:
        score += ACTIVITY_TYPE_FIT_SCORE
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
    elif criteria.duration_limit_minutes is not None:
        if duration_minutes is None:
            score += PLACE_DURATION_NEUTRAL_SCORE
        elif duration_minutes <= criteria.duration_limit_minutes:
            score += DURATION_FIT_SCORE
    if pref_matched:
        score += PREFERENCE_FIT_SCORE
    if occasion_matched:
        score += OCCASION_FIT_SCORE
    if temporal_matched:
        score += TEMPORAL_FIT_SCORE
    if desc_matched > 0:
        score += desc_matched * SEMANTIC_MATCH_SCORE
    return score


def _assess_exclusions(
    category: InformationCategory,
    name: str,
    description: str,
    cost: Decimal | None,
    metadata: dict[str, str],
    exclusions: tuple[str, ...],
    reasons: list[DecisionReason],
    setting_preference: str | None = None,
    weather_context: str | None = None,
) -> bool:
    is_eligible = True
    combined_text = f"{name} {description}".casefold()
    for raw_exclusion in exclusions:
        ex = raw_exclusion.casefold().replace(" ", "_")
        if ex in {"no_outdoors", "no_outdoor", "not_outdoors", "nothing_outdoors"}:
            is_outdoor = (
                category is InformationCategory.NATURE
                or metadata.get("weather_sensitive") == "true"
                or metadata.get("outdoor") == "true"
                or "outdoor" in combined_text
                or "trail" in combined_text
                or "hike" in combined_text
                or "mountain" in combined_text
                or "beach" in combined_text
            )
            if is_outdoor:
                reasons.append(
                    DecisionReason(
                        ReasonType.EXCLUSION,
                        ReasonOutcome.VIOLATED,
                        "Excluded: outdoor activity violates constraint",
                    )
                )
                is_eligible = False
        elif ex in {"no_alcohol", "non_alcoholic", "sober", "no_drinking"}:
            is_alcohol = (
                "bar" in combined_text.split()
                or "cocktails" in combined_text
                or "cocktail" in combined_text
                or "brewery" in combined_text
                or "pub" in combined_text.split()
                or "wine tasting" in combined_text
                or "wine bar" in combined_text
                or metadata.get("alcohol") in {"true", "only"}
            )
            if is_alcohol:
                reasons.append(
                    DecisionReason(
                        ReasonType.EXCLUSION,
                        ReasonOutcome.VIOLATED,
                        "Excluded: alcohol-centered venue violates non-drinking constraint",
                    )
                )
                is_eligible = False
        elif ex in {"not_fancy", "not_too_fancy", "nothing_too_fancy", "no_fancy"}:
            is_fancy = "fine dining" in combined_text or "upscale" in combined_text or (cost is not None and cost >= Decimal("400"))
            if is_fancy:
                reasons.append(
                    DecisionReason(
                        ReasonType.EXCLUSION,
                        ReasonOutcome.VIOLATED,
                        "Excluded: upscale / formal venue violates constraint",
                    )
                )
                is_eligible = False
        elif ex in {"no_clubs", "no_club", "no_party"}:
            if "club" in combined_text or "nightclub" in combined_text:
                reasons.append(
                    DecisionReason(
                        ReasonType.EXCLUSION,
                        ReasonOutcome.VIOLATED,
                        "Excluded: clubs or party venues violate constraint",
                    )
                )
                is_eligible = False

    if setting_preference == "indoor" or weather_context == "raining":
        is_outdoor = (
            category is InformationCategory.NATURE
            or metadata.get("weather_sensitive") == "true"
            or metadata.get("outdoor") == "true"
            or "outdoor" in combined_text
            or "trail" in combined_text
            or "hike" in combined_text
            or "mountain" in combined_text
            or "beach" in combined_text
        )
        if is_outdoor and is_eligible:
            reasons.append(
                DecisionReason(
                    ReasonType.SETTING,
                    ReasonOutcome.VIOLATED,
                    "Excluded: outdoor venue violates indoor/weather constraint",
                )
            )
            is_eligible = False

    return is_eligible


def _assess_preferences(
    category: InformationCategory,
    description: str,
    preferences: tuple[str, ...],
    reasons: list[DecisionReason],
) -> bool:
    matched = False
    desc_lower = description.casefold()
    for raw_pref in preferences:
        pref = raw_pref.casefold()
        if pref in {"casual", "chill", "relaxed", "unhurried"}:
            if any(term in desc_lower for term in ("casual", "relaxed", "walk", "tasting", "green space", "coffee", "roastery")):
                reasons.append(
                    DecisionReason(
                        ReasonType.PREFERENCE,
                        ReasonOutcome.SUPPORTED,
                        "Fits your preference for a relaxed, casual vibe",
                    )
                )
                matched = True
        elif pref in {"nice", "somewhere nice", "aesthetic", "scenic"}:
            if any(term in desc_lower for term in ("waterfront", "green space", "guided-history", "tasting", "roastery", "view", "walk", "cultural")):
                reasons.append(
                    DecisionReason(
                        ReasonType.PREFERENCE,
                        ReasonOutcome.SUPPORTED,
                        "Fits your preference for somewhere nice and pleasant",
                    )
                )
                matched = True
        elif pref in {"romantic", "date"}:
            if any(term in desc_lower for term in ("shared", "tasting", "waterfront", "walk", "cultural", "relaxed")):
                reasons.append(
                    DecisionReason(
                        ReasonType.PREFERENCE,
                        ReasonOutcome.SUPPORTED,
                        "Matches your preference for a romantic outing",
                    )
                )
                matched = True
        elif pref in {"fun", "something fun", "entertainment", "social"}:
            reasons.append(
                DecisionReason(
                    ReasonType.PREFERENCE,
                    ReasonOutcome.SUPPORTED,
                    "Matches your preference for something fun and engaging",
                )
            )
            matched = True
        elif pref in {"food", "food-focused", "food_focused"}:
            if category is InformationCategory.FOOD:
                reasons.append(
                    DecisionReason(
                        ReasonType.PREFERENCE,
                        ReasonOutcome.SUPPORTED,
                        "Matches your food-focused preference",
                    )
                )
                matched = True
        elif pref in {"culture", "cultural"}:
            if category is InformationCategory.CULTURE:
                reasons.append(
                    DecisionReason(
                        ReasonType.PREFERENCE,
                        ReasonOutcome.SUPPORTED,
                        "Matches your cultural preference",
                    )
                )
                matched = True
        elif pref in {"outdoors", "nature"}:
            if category is InformationCategory.NATURE:
                reasons.append(
                    DecisionReason(
                        ReasonType.PREFERENCE,
                        ReasonOutcome.SUPPORTED,
                        "Matches your outdoors preference",
                    )
                )
                matched = True
    return matched


def _assess_occasion(
    category: InformationCategory,
    description: str,
    occasion: str | None,
    reasons: list[DecisionReason],
) -> bool:
    if occasion is None:
        return False
    occ = occasion.casefold()
    desc_lower = description.casefold()
    if occ == "date":
        if any(term in desc_lower for term in ("shared", "waterfront", "walk", "tasting", "guided", "relaxed")) or category in (
            InformationCategory.FOOD,
            InformationCategory.CULTURE,
            InformationCategory.NATURE,
        ):
            reasons.append(
                DecisionReason(
                    ReasonType.OCCASION,
                    ReasonOutcome.SUPPORTED,
                    "Well suited for a date outing",
                )
            )
            return True
    elif occ in {"birthday", "celebration"}:
        if category in (InformationCategory.FOOD, InformationCategory.ENTERTAINMENT):
            reasons.append(
                DecisionReason(
                    ReasonType.OCCASION,
                    ReasonOutcome.SUPPORTED,
                    "Great choice for celebrating a special occasion",
                )
            )
            return True
    elif occ in {"friends", "casual_hangout"}:
        reasons.append(
            DecisionReason(
                ReasonType.OCCASION,
                ReasonOutcome.SUPPORTED,
                "Great fit for a casual get-together with friends",
            )
        )
        return True
    elif occ == "solo":
        if "self-guided" in desc_lower or "walk" in desc_lower or category in (InformationCategory.NATURE, InformationCategory.CULTURE):
            reasons.append(
                DecisionReason(
                    ReasonType.OCCASION,
                    ReasonOutcome.SUPPORTED,
                    "Ideal for an unhurried solo experience",
                )
            )
            return True
    return False


def _assess_semantic_descriptors(
    name: str,
    description: str,
    metadata: Mapping[str, str],
    descriptors: tuple[str, ...],
    reasons: list[DecisionReason],
) -> int:
    if not descriptors:
        return 0
    matched_count = 0
    combined_text = f"{name} {description}".casefold()
    meta_values = " ".join(metadata.values()).casefold() if metadata else ""
    full_text = f"{combined_text} {meta_values}"
    stopwords = {"and", "the", "for", "with", "themed", "vibe", "style", "setting"}

    for descriptor in descriptors:
        desc_clean = descriptor.strip().casefold()
        if not desc_clean:
            continue
        if desc_clean in full_text:
            matched_count += 1
            reasons.append(
                DecisionReason(
                    ReasonType.SEMANTIC_MATCH,
                    ReasonOutcome.SUPPORTED,
                    f"Supports requested '{descriptor}' vibe",
                )
            )
            continue

        tokens = [t for t in re.findall(r"\w+", desc_clean) if len(t) > 2 and t not in stopwords]
        if tokens and all(t in full_text for t in tokens):
            matched_count += 1
            reasons.append(
                DecisionReason(
                    ReasonType.SEMANTIC_MATCH,
                    ReasonOutcome.SUPPORTED,
                    f"Supports requested '{descriptor}' vibe ({', '.join(tokens)})",
                )
            )
        else:
            reasons.append(
                DecisionReason(
                    ReasonType.SEMANTIC_MATCH,
                    ReasonOutcome.NEUTRAL,
                    f"'{descriptor}' aesthetic could not be verified from public registry",
                )
            )
    return matched_count


def _generate_trade_off_summary(
    criteria: DecisionCriteria,
    candidates: list[DecisionCandidate],
) -> str | None:
    if not candidates:
        return None
    eligible = [c for c in candidates if c.is_eligible]
    if not eligible:
        return None
    top_candidates = eligible[:3]

    notes: list[str] = []
    if criteria.semantic_descriptors:
        unverified: list[str] = []
        for desc in criteria.semantic_descriptors:
            supported = any(
                any(
                    r.type is ReasonType.SEMANTIC_MATCH
                    and r.outcome is ReasonOutcome.SUPPORTED
                    and desc.casefold() in r.message.casefold()
                    for r in c.reasons
                )
                for c in top_candidates
            )
            if not supported:
                unverified.append(desc)
        if unverified:
            desc_str = ", ".join(f"'{d}'" for d in unverified)
            notes.append(
                f"Public registry listings do not currently verify {desc_str} decor/ambiance; recommendations were prioritized for quality and constraints in Cape Town."
            )

    if notes:
        return " ".join(notes)
    return None

