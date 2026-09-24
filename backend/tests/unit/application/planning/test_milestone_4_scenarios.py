"""Milestone 4 Scenario Verification Tests.

Verifies Scenarios A through F against the complete temporal planning pipeline.
"""
from decimal import Decimal
from uuid import uuid4
import pytest

from app.application.planning.dtos import PlanningIntent
from app.application.planning.planning_service import PlanningService
from app.application.planning.selection_service import criteria_from_plan
from app.application.planning.understanding_service import DeterministicUnderstandingEngine
from app.domain.entities.planning.constraint import ConstraintType
from app.domain.entities.planning.decision import DecisionCriteria, ReasonOutcome, ReasonType
from app.domain.entities.planning.decision_engine import decide
from app.domain.entities.planning.information import InformationCategory, Place
from app.domain.entities.planning.plan import Plan
from app.domain.entities.planning.plan_item import PlanItem
from app.domain.entities.planning.temporal import (
    DayOfWeek,
    DaySchedule,
    OpeningHoursSchedule,
    TimeRange,
    parse_opening_hours,
)


class InMemoryPlanRepository:
    def __init__(self) -> None:
        self._plans: dict[tuple[object, object], Plan] = {}

    async def create(self, plan: Plan) -> Plan:
        self._plans[(plan.id, plan.user_id)] = plan
        return plan

    async def update(self, plan: Plan) -> Plan:
        self._plans[(plan.id, plan.user_id)] = plan
        return plan

    async def get(self, plan_id: object, user_id: object) -> Plan | None:
        return self._plans.get((plan_id, user_id))


@pytest.fixture
def understanding_engine() -> DeterministicUnderstandingEngine:
    return DeterministicUnderstandingEngine()


@pytest.fixture
def planning_service() -> PlanningService:
    return PlanningService(InMemoryPlanRepository())


def test_scenario_a_date_temporal_understanding(understanding_engine: DeterministicUnderstandingEngine) -> None:
    """Scenario A: Date with boyfriend Saturday around 11 until 7, R800, not too fancy."""
    req = "I want to take my boyfriend somewhere nice Saturday, maybe R800, around 11 until 7, somewhere around town, but nothing too fancy."
    u = understanding_engine.parse(req)

    assert u.occasion == "date"
    assert u.relationship_context == "boyfriend"
    assert u.date_spec == "Saturday"
    assert u.start_time == "11:00"
    assert u.end_time == "19:00"
    assert u.time_confidence == "approximate"
    assert u.budget_amount == Decimal("800")
    assert "not_too_fancy" in u.exclusions
    assert u.location == "Cape Town"


def test_scenario_b_birthday_family_afternoon(understanding_engine: DeterministicUnderstandingEngine) -> None:
    """Scenario B: Mom's birthday Saturday afternoon, R1000, 3 people."""
    req = "It's my mom's birthday on Saturday afternoon, we have about R1000, maybe 3 people."
    u = understanding_engine.parse(req)

    assert u.occasion == "birthday"
    assert u.relationship_context == "mom"
    assert u.date_spec == "Saturday"
    assert u.time_window == "afternoon"
    assert u.start_time == "12:30"
    assert u.end_time == "17:30"
    assert u.budget_amount == Decimal("1000")
    assert u.people_count == 3


def test_scenario_c_duration_limit(understanding_engine: DeterministicUnderstandingEngine) -> None:
    """Scenario C: Hard 3-hour constraint on Saturday afternoon."""
    req = "We only have three hours Saturday afternoon for something fun."
    u = understanding_engine.parse(req)

    assert u.duration_limit_minutes == 180
    assert u.date_spec == "Saturday"
    assert u.time_window == "afternoon"


def test_scenario_d_closed_venue_handling() -> None:
    """Scenario D: Venue that is closed on the requested day/time is assessed correctly."""
    # Zeitz MOCAA is closed on Mondays (Tue-Sun 10:00-18:00)
    place = Place(
        id=uuid4(),
        name="Zeitz MOCAA",
        category=InformationCategory.CULTURE,
        location="Cape Town",
        description="Museum",
        opening_hours="Tue-Sun 10:00-18:00",
    )

    # 1. Monday check -> Closed
    crit_monday = DecisionCriteria(
        location="Cape Town",
        day_of_week=DayOfWeek.MONDAY,
        start_time="11:00",
    )
    result_mon = decide(crit_monday, [place], [])
    mon_cand = result_mon.candidates[0]
    assert not mon_cand.is_eligible
    reason_mon = next(r for r in mon_cand.reasons if r.type == ReasonType.OPENING_HOURS)
    assert reason_mon.outcome == ReasonOutcome.VIOLATED
    assert "Closed on Monday" in reason_mon.message

    # 2. Tuesday at 11:00 check -> Open
    crit_tuesday = DecisionCriteria(
        location="Cape Town",
        day_of_week=DayOfWeek.TUESDAY,
        start_time="11:00",
    )
    result_tue = decide(crit_tuesday, [place], [])
    tue_cand = result_tue.candidates[0]
    assert tue_cand.is_eligible
    reason_tue = next(r for r in tue_cand.reasons if r.type == ReasonType.OPENING_HOURS)
    assert reason_tue.outcome == ReasonOutcome.SUPPORTED
    assert "Open on Tuesday" in reason_tue.message


def test_scenario_e_unlisted_opening_hours_honest_language() -> None:
    """Scenario E: Unlisted opening hours remain neutral and never fabricate."""
    place = Place(
        id=uuid4(),
        name="Secret Viewpoint",
        category=InformationCategory.NATURE,
        location="Cape Town",
        description="Viewpoint",
        opening_hours=None,
    )


    crit = DecisionCriteria(
        location="Cape Town",
        day_of_week=DayOfWeek.SATURDAY,
        start_time="14:00",
    )
    result = decide(crit, [place], [])
    cand = result.candidates[0]
    # Neutral fit: not disqualified, but clearly unverified
    assert cand.is_eligible
    reason = next(r for r in cand.reasons if r.type == ReasonType.OPENING_HOURS)
    assert reason.outcome == ReasonOutcome.NEUTRAL
    assert "Opening hours could not be verified" in reason.message
    assert "recommend checking" in reason.message



@pytest.mark.asyncio
async def test_scenario_f_conversational_temporal_tweaks(planning_service: PlanningService) -> None:
    """Scenario F: Conversational modifications to shift time, set deadline, and limit duration."""
    user_id = uuid4()
    understanding = DeterministicUnderstandingEngine().parse("Saturday around 11 until 7 budget R800")
    plan = await planning_service.create_plan_from_understanding(user_id, understanding)

    assert plan.context.start_time.hour == 11
    assert plan.context.end_time.hour == 19

    # Tweak 1: "Make it start later"
    plan_t1 = await planning_service.modify_plan(user_id, plan.id, "Make it start later")
    assert plan_t1.context.start_time.hour == 13
    assert any(c.value == "start_time:13:00" for c in plan_t1.constraints)

    # Tweak 2: "Need to be home by 6"
    plan_t2 = await planning_service.modify_plan(user_id, plan.id, "I need to be home by 6")
    assert plan_t2.context.end_time.hour == 18
    assert any(c.value == "end_time:18:00" for c in plan_t2.constraints)

    # Tweak 3: "We only have three hours"
    plan_t3 = await planning_service.modify_plan(user_id, plan.id, "We only have three hours")
    dur_c = next(c for c in plan_t3.constraints if c.type is ConstraintType.TIME_MAX)
    assert dur_c.numeric_value == Decimal("180")
