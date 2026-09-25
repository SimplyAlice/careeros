"""Comprehensive M13 planning intelligence test suite covering 25+ real-world constraint scenarios."""
from decimal import Decimal
from uuid import uuid4
import pytest

from app.application.planning.adaptation_service import PlanAdaptationService
from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.information import PlanningInformationService
from app.application.planning.planning_service import PlanningService
from app.application.planning.travel_provider import DefaultTravelTimeProvider
from app.application.planning.understanding_service import DeterministicUnderstandingEngine
from app.domain.entities.planning.constraints import BudgetStyle, TravelProviderKind
from app.domain.entities.planning.decision import DecisionCriteria, ReasonOutcome, ReasonType
from app.domain.entities.planning.decision_engine import decide
from app.domain.entities.planning.information import InformationCategory
from app.domain.entities.planning.understanding import BudgetKind
from app.infrastructure.planning.fixture_provider import CapeTownFixtureInformationProvider


class MemoryPlanRepository:
    def __init__(self):
        self.plans = {}
        self.items = {}

    async def create(self, plan):
        self.plans[plan.id] = plan
        return plan

    async def get(self, plan_id, user_id):
        return self.plans.get(plan_id)

    async def list_for_user(self, user_id):
        return [p for p in self.plans.values() if p.user_id == user_id]

    async def update(self, plan):
        self.plans[plan.id] = plan
        return plan

    async def delete(self, plan_id, user_id):
        if plan_id in self.plans:
            del self.plans[plan_id]
            return True
        return False

    async def create_item(self, user_id, plan_id, item):
        self.items.setdefault(plan_id, []).append(item)
        if plan_id in self.plans:
            self.plans[plan_id].items.append(item)
        return item

    async def list_items(self, user_id, plan_id):
        return self.items.get(plan_id, [])

    async def get_item(self, user_id, plan_id, item_id):
        for i in self.items.get(plan_id, []):
            if i.id == item_id:
                return i
        return None

    async def update_item(self, user_id, plan_id, item):
        return item

    async def delete_item(self, user_id, plan_id, item_id):
        if plan_id in self.items:
            self.items[plan_id] = [i for i in self.items[plan_id] if i.id != item_id]
            return True
        return False


@pytest.fixture
def engine():
    return DeterministicUnderstandingEngine()


@pytest.fixture
def places():
    return list(CapeTownFixtureInformationProvider._places)


@pytest.fixture
def activities():
    return list(CapeTownFixtureInformationProvider._activities)


# 1. Budget Intelligence: Nuanced styles
def test_budget_per_person(engine):
    u = engine.parse("We have R250 each for three people.")
    assert u.people_count == 3
    assert u.budget_amount == Decimal("250")
    assert u.budget_model.style == BudgetStyle.PER_PERSON
    assert u.budget_model.effective_limit(3) == Decimal("750")


def test_budget_hard_ceiling(engine):
    u = engine.parse("Under R500 maximum for lunch.")
    assert u.budget_amount == Decimal("500")
    assert u.budget_kind == BudgetKind.HARD_MAX
    assert u.budget_model.style == BudgetStyle.HARD_CEILING


def test_budget_flexible_stretch(engine):
    u = engine.parse("Budget around R400 but can stretch to R700 if needed.")
    assert u.budget_amount == Decimal("400")
    assert u.budget_model.stretch_amount == Decimal("700")
    assert u.budget_model.style == BudgetStyle.FLEXIBLE_STRETCH


def test_budget_priority_cheap(engine):
    u = engine.parse("Keep it cheap, on a budget for Saturday afternoon.")
    assert u.budget_kind == BudgetKind.PREFERENCE
    assert u.budget_model.style == BudgetStyle.PRIORITY_CHEAP


def test_budget_spend_most_on_dinner(engine):
    u = engine.parse("Under R600 but I want to spend most of it on dinner.")
    assert u.budget_amount == Decimal("600")
    assert u.budget_model.priority_note == "spend_most_on_dinner"
    assert "food_focused" in u.preferences or "prioritize_dinner" in u.preferences


def test_budget_temporal_free_not_zero_cost(engine):
    u = engine.parse("I have two hours free tomorrow afternoon in Cape Town, need somewhere to read.")
    assert u.budget_amount is None
    assert u.budget_kind == BudgetKind.NONE
    assert u.duration_limit_minutes == 120


def test_budget_explicit_zero_cost(engine):
    u = engine.parse("Free of charge activities only, zero budget.")
    assert u.budget_amount == Decimal("0")
    assert u.budget_kind == BudgetKind.HARD_MAX


# 2. Time & Schedule Intelligence
def test_time_dinner_after_7_leave_by_9(engine):
    u = engine.parse("Dinner after 7 but I need to leave by 9.")
    assert u.start_time == "19:00"
    assert u.end_time == "21:00"
    assert u.deadline == "21:00"


def test_time_span_exact(engine):
    u = engine.parse("Outing from 2pm to 6pm on Sunday.")
    assert u.date_spec == "Sunday"
    assert u.start_time == "14:00"
    assert u.end_time == "18:00"


def test_time_duration_limit(engine):
    u = engine.parse("I only have three hours free before I need to be home.")
    assert u.duration_limit_minutes == 180


def test_time_whole_afternoon(engine):
    u = engine.parse("Free for the whole afternoon on Saturday.")
    assert u.date_spec == "Saturday"
    assert u.time_window == "afternoon"
    assert u.duration_limit_minutes == 240


def test_time_after_work(engine):
    u = engine.parse("Drinks after work on Friday.")
    assert u.date_spec == "Friday"
    assert u.time_window == "after_work"
    assert u.start_time == "17:30"


# 3. Weather & Environment Reasoning
def test_weather_rain_indoor_preference(engine):
    u = engine.parse("It's raining and we don't want to get wet, keep it indoors.")
    assert u.weather_context == "raining"
    assert u.setting_preference == "indoor"
    assert "no_outdoors" in u.exclusions


def test_weather_sunny_outdoor_preference(engine):
    u = engine.parse("It's sunny, let's do something outdoors in the sun.")
    assert u.weather_context == "sunny"
    assert u.setting_preference == "outdoor"


# 4. Exclusions & Negative Preferences
def test_exclusion_sober_non_drinker(engine, places, activities):
    u = engine.parse("My friend doesn't drink alcohol, neither of us drinks.")
    assert "no_alcohol" in u.exclusions
    assert u.people_count == 2
    criteria = DecisionCriteria(exclusions=u.exclusions)
    res = decide(criteria, places, activities)
    for c in res.eligible:
        name_lower = c.name.lower()
        assert "bar" not in name_lower.split()
        assert "brewery" not in name_lower
        assert "wine tasting" not in name_lower


def test_exclusion_loud_bars(engine, places, activities):
    u = engine.parse("Anywhere except loud bars or clubs.")
    assert "no_loud_bars" in u.exclusions or "no_clubs" in u.exclusions


def test_exclusion_not_fancy(engine, places, activities):
    u = engine.parse("Nothing too fancy, casual spot only.")
    assert "not_too_fancy" in u.exclusions
    criteria = DecisionCriteria(exclusions=u.exclusions)
    res = decide(criteria, places, activities)
    for c in res.eligible:
        assert "fine dining" not in f"{c.name} {c.address or ''}".lower()


# 5. Travel & Feasibility Provider
@pytest.mark.asyncio
async def test_travel_time_provider_matrix():
    provider = DefaultTravelTimeProvider()
    est = await provider.estimate("Waterfront Harbour Hall", "Cape Town", "Bo-Kaap Cultural Stop", "Cape Town")
    assert est.duration_minutes == 10
    assert est.provider_kind == TravelProviderKind.STATIC_ESTIMATE

    # Unknown origin falls back gracefully to conservative buffer
    fallback = await provider.estimate("Unknown Spot A", None, "Unknown Spot B", None)
    assert fallback.duration_minutes == 15
    assert fallback.provider_kind == TravelProviderKind.CONSERVATIVE_FALLBACK


# 6. Trade-Off Engine & Conflicting Constraints
def test_trade_off_fancy_dinner_under_r200(engine, places, activities):
    u = engine.parse("Fancy dinner for two under R200.")
    assert u.people_count == 2
    assert u.budget_amount == Decimal("200")
    assert "fancy" in u.semantic_descriptors

    criteria = DecisionCriteria(
        maximum_cost=u.budget_amount,
        group_size=u.people_count,
        semantic_descriptors=u.semantic_descriptors,
    )
    res = decide(criteria, places, activities)
    assert res.trade_off_summary is not None
    assert "I couldn't verify a dinner option that is both upscale and within R200" in res.trade_off_summary
    assert "higher-cost alternative if you're willing to stretch" in res.trade_off_summary
    # Ensure hard constraint was preserved: no eligible candidate violates the R200 limit
    for c in res.eligible:
        if c.cost is not None:
            assert c.cost <= Decimal("200")


def test_trade_off_rain_with_outdoor_preference(engine, places, activities):
    u = engine.parse("Outdoor nature walk while it's raining.")
    criteria = DecisionCriteria(
        preferences=("outdoors",),
        weather_context="raining",
        setting_preference="indoor",
    )
    res = decide(criteria, places, activities)
    assert res.trade_off_summary is not None
    assert "Rain is expected" in res.trade_off_summary
    assert "sheltered and indoor options were prioritised" in res.trade_off_summary


def test_trade_off_deadline_scheduled(engine, places, activities):
    criteria = DecisionCriteria(
        deadline="21:00",
        start_time="19:00",
        end_time="21:00",
    )
    res = decide(criteria, places, activities)
    assert res.trade_off_summary is not None
    assert "21:00" in res.trade_off_summary


# 7. Semantic Matching & Evidence Provenance
def test_evidence_provenance_marking(engine, places, activities):
    criteria = DecisionCriteria(
        semantic_descriptors=("quiet", "dimly lit"),
    )
    res = decide(criteria, places, activities)
    for c in res.candidates:
        semantic_reasons = [r for r in c.reasons if r.type is ReasonType.SEMANTIC_MATCH]
        for r in semantic_reasons:
            if r.outcome is ReasonOutcome.SUPPORTED:
                assert r.evidence_status in {"verified", "probable"}
            elif r.outcome is ReasonOutcome.NEUTRAL:
                assert r.evidence_status == "unknown"


# 8. Multi-Constraint Realistic Scenario (M13 Core Test)
def test_complex_multi_constraint_scenario(engine, places, activities):
    prompt = (
        "My friend is visiting Cape Town tomorrow. We have R600, neither of us drinks, "
        "it's supposed to rain, and we need to be home by 10. We'd like somewhere pretty for dinner."
    )
    u = engine.parse(prompt)
    assert u.people_count == 2
    assert u.location == "Cape Town"
    assert u.budget_amount == Decimal("600")
    assert "no_alcohol" in u.exclusions
    assert "no_outdoors" in u.exclusions
    assert u.weather_context == "raining"
    assert u.setting_preference == "indoor"
    assert u.deadline == "22:00"
    assert u.date_spec == "Tomorrow"

    criteria = DecisionCriteria(
        location=u.location,
        maximum_cost=u.budget_amount,
        group_size=u.people_count,
        exclusions=u.exclusions,
        setting_preference=u.setting_preference,
        weather_context=u.weather_context,
        deadline=u.deadline,
        semantic_descriptors=u.semantic_descriptors,
    )
    res = decide(criteria, places, activities)
    assert len(res.eligible) > 0
    for c in res.eligible:
        # Excludes outdoor places
        assert c.category is not InformationCategory.NATURE
        # Excludes alcohol
        assert "bar" not in c.name.lower().split()
        # Fits budget
        if c.cost is not None:
            assert c.cost <= Decimal("600")


# 9. Adaptation Integration Test
@pytest.mark.asyncio
async def test_adaptation_service_makes_it_cheaper():
    repo = MemoryPlanRepository()
    plans = PlanningService(repo)
    engine = DeterministicUnderstandingEngine()
    info = PlanningInformationService(CapeTownFixtureInformationProvider())
    decisions = PlanningDecisionService(info)
    adaptation_service = PlanAdaptationService(plans, decisions, info)

    u = engine.parse("Dinner date in Cape Town, budget R800.")
    user_id = uuid4()
    plan = await plans.create_plan_from_understanding(user_id, u)

    # Propose adaptation: Make it cheaper
    adaptation = await adaptation_service.propose_adaptation(user_id, plan.id, "Make it cheaper")
    assert adaptation is not None
    assert len(adaptation.narrative_summary) > 0
    # New budget should be reduced
    assert adaptation.new_total_cost is not None
    assert adaptation.new_total_cost < Decimal("800")
