from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.information import PlanningInformationService
from app.application.planning.selection_service import criteria_from_plan
from app.application.planning.understanding_service import DeterministicUnderstandingEngine
from app.domain.entities.planning.decision import ReasonOutcome, ReasonType
from app.domain.entities.planning.information import InformationCategory
from app.infrastructure.planning.openstreetmap_provider import OpenStreetMapInformationProvider


@pytest.fixture
def understanding_engine() -> DeterministicUnderstandingEngine:
    return DeterministicUnderstandingEngine()


@pytest.fixture
def information_service() -> PlanningInformationService:
    provider = OpenStreetMapInformationProvider(enable_network=False)
    return PlanningInformationService(provider)


@pytest.fixture
def decision_service(information_service: PlanningInformationService) -> PlanningDecisionService:
    return PlanningDecisionService(information_service)


class TestOpenEndedRegressionPrompts:
    """Verify that the 5 diagnostic failure prompts now succeed across the entire pipeline."""

    @pytest.mark.asyncio
    async def test_prompt_1_quiet_dark_themed_restaurant(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "lunch for two in a quiet dark themed restaurent, budget R500"
        u = understanding_engine.parse(raw)

        # 1. Intent model checks
        assert u.people_count == 2
        assert u.budget_amount == Decimal("500")
        assert u.location == "Cape Town"
        assert u.location_is_inferred is True
        assert "quiet" in u.semantic_descriptors
        assert "dark themed" in u.semantic_descriptors
        assert InformationCategory.FOOD in u.activity_types

        # 2. Decision engine & retrieval
        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            category=InformationCategory.FOOD,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            semantic_descriptors=u.semantic_descriptors,
            time_window=u.time_window,
        )
        result = await decision_service.recommend(crit)
        eligible = [c for c in result.candidates if c.is_eligible]

        assert len(eligible) > 0, "Should return eligible dining venues"
        assert all(c.category is InformationCategory.FOOD for c in eligible)
        assert all(c.cost is None or c.cost <= Decimal("500") for c in eligible)

        # 3. Honest trade-off summary
        assert result.trade_off_summary is not None
        assert "dark themed" in result.trade_off_summary.lower()
        assert "unverified" in result.trade_off_summary.lower() or "not currently verify" in result.trade_off_summary.lower()

    @pytest.mark.asyncio
    async def test_prompt_2_two_hours_free_tomorrow(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "I have R300 and two hours free tomorrow afternoon in Cape Town"
        u = understanding_engine.parse(raw)

        # Budget should be R300, NOT R0 from 'free'
        assert u.budget_amount == Decimal("300")
        assert u.duration_limit_minutes == 120
        assert u.location == "Cape Town"
        assert u.date_spec == "Tomorrow"
        assert u.time_window == "afternoon"

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            maximum_cost=u.budget_amount,
            duration_limit_minutes=u.duration_limit_minutes,
            time_window=u.time_window,
        )
        result = await decision_service.recommend(crit)
        eligible = [c for c in result.candidates if c.is_eligible]
        assert len(eligible) > 0
        assert all(c.cost is None or c.cost <= Decimal("300") for c in eligible)

    @pytest.mark.asyncio
    async def test_prompt_3_friend_does_not_drink(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "My friend doesn't drink and we want something fun to do tonight around R600"
        u = understanding_engine.parse(raw)

        assert u.people_count == 2
        assert u.budget_amount == Decimal("600")
        assert "no_alcohol" in u.exclusions
        assert u.location == "Cape Town"

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            exclusions=u.exclusions,
            preferences=u.preferences,
        )
        result = await decision_service.recommend(crit)
        eligible = [c for c in result.candidates if c.is_eligible]
        assert len(eligible) > 0

        # No alcohol-focused bars or breweries should be eligible
        for cand in eligible:
            name_lower = cand.name.lower()
            assert "bar" not in name_lower.split(), f"Bar should be disqualified: {cand.name}"
            assert "cocktail" not in name_lower, f"Cocktail spot should be disqualified: {cand.name}"
            assert "brewery" not in name_lower, f"Brewery should be disqualified: {cand.name}"

    @pytest.mark.asyncio
    async def test_prompt_4_three_of_us_dress_up_and_photos(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "three of us want to dress up and take photos this Saturday evening in Cape Town"
        u = understanding_engine.parse(raw)

        assert u.people_count == 3
        assert u.date_spec == "Saturday"
        assert u.time_window == "evening"
        assert u.location == "Cape Town"
        assert "dress up" in u.semantic_descriptors
        assert "take photos" in u.semantic_descriptors

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            group_size=u.people_count,
            semantic_descriptors=u.semantic_descriptors,
            day_of_week=u.date_spec,
            time_window=u.time_window,
        )
        result = await decision_service.recommend(crit)
        eligible = [c for c in result.candidates if c.is_eligible]
        assert len(eligible) > 0

    @pytest.mark.asyncio
    async def test_prompt_5_raining_indoor_family_with_2_kids(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "raining in Cape Town, need indoor activities for family with 2 kids under R1000"
        u = understanding_engine.parse(raw)

        assert u.people_count == 4
        assert u.budget_amount == Decimal("1000")
        assert u.weather_context == "raining"
        assert u.setting_preference == "indoor"
        assert "no_outdoors" in u.exclusions
        assert u.location == "Cape Town"

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            exclusions=u.exclusions,
            setting_preference=u.setting_preference,
            weather_context=u.weather_context,
        )
        result = await decision_service.recommend(crit)
        eligible = [c for c in result.candidates if c.is_eligible]
        assert len(eligible) > 0

        # All outdoor activities and nature stops should be excluded
        for cand in eligible:
            assert cand.category is not InformationCategory.NATURE, f"Nature should be excluded in rain: {cand.name}"
            name_lower = cand.name.lower()
            assert "hike" not in name_lower
            assert "trail" not in name_lower
            assert "beach" not in name_lower


class TestOpenEndedGeneralityUnseenPrompts:
    """Verify that 5 completely new unseen prompts are understood and planned correctly."""

    @pytest.mark.asyncio
    async def test_unseen_1_outdoor_seating_sunday_dinner(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "dinner for 4 this Sunday evening with outdoor seating under R1200"
        u = understanding_engine.parse(raw)

        assert u.people_count == 4
        assert u.budget_amount == Decimal("1200")
        assert u.date_spec == "Sunday"
        assert u.time_window == "evening"
        assert u.setting_preference == "outdoor"
        assert InformationCategory.FOOD in u.activity_types

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location="Cape Town",
            category=InformationCategory.FOOD,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            setting_preference=u.setting_preference,
        )
        result = await decision_service.recommend(crit)
        assert len([c for c in result.candidates if c.is_eligible]) > 0

    @pytest.mark.asyncio
    async def test_unseen_2_solo_coffee_and_reading(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "solo coffee and reading spot in Cape Town tomorrow morning, R150"
        u = understanding_engine.parse(raw)

        assert u.people_count == 1
        assert u.budget_amount == Decimal("150")
        assert u.date_spec == "Tomorrow"
        assert u.time_window == "morning"
        assert "coffee" in u.semantic_descriptors
        assert "reading" in u.semantic_descriptors

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            semantic_descriptors=u.semantic_descriptors,
        )
        result = await decision_service.recommend(crit)
        assert len([c for c in result.candidates if c.is_eligible]) > 0

    @pytest.mark.asyncio
    async def test_unseen_3_anniversary_romantic_dinner(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "anniversary celebration for two, quiet romantic dinner under R1500"
        u = understanding_engine.parse(raw)

        assert u.people_count == 2
        assert u.budget_amount == Decimal("1500")
        assert "quiet" in u.semantic_descriptors
        assert "romantic" in u.semantic_descriptors

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location="Cape Town",
            category=InformationCategory.FOOD,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            semantic_descriptors=u.semantic_descriptors,
        )
        result = await decision_service.recommend(crit)
        assert len([c for c in result.candidates if c.is_eligible]) > 0

    @pytest.mark.asyncio
    async def test_unseen_4_group_entertainment_under_budget(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "group games or entertainment for 6 people under R900"
        u = understanding_engine.parse(raw)

        assert u.people_count == 6
        assert u.budget_amount == Decimal("900")
        assert "games" in u.semantic_descriptors

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location="Cape Town",
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            semantic_descriptors=u.semantic_descriptors,
        )
        result = await decision_service.recommend(crit)
        assert len([c for c in result.candidates if c.is_eligible]) > 0

    @pytest.mark.asyncio
    async def test_unseen_5_bad_weather_indoor_museum(
        self,
        understanding_engine: DeterministicUnderstandingEngine,
        decision_service: PlanningDecisionService,
    ) -> None:
        raw = "bad weather in Cape Town, indoor museum or culture outing for two, R400"
        u = understanding_engine.parse(raw)

        assert u.people_count == 2
        assert u.budget_amount == Decimal("400")
        assert u.weather_context == "raining"
        assert u.setting_preference == "indoor"
        assert "no_outdoors" in u.exclusions
        assert InformationCategory.CULTURE in u.activity_types

        from app.domain.entities.planning.decision import DecisionCriteria
        crit = DecisionCriteria(
            location=u.location,
            category=InformationCategory.CULTURE,
            maximum_cost=u.budget_amount,
            group_size=u.people_count,
            setting_preference=u.setting_preference,
            weather_context=u.weather_context,
            exclusions=u.exclusions,
        )
        result = await decision_service.recommend(crit)
        eligible = [c for c in result.candidates if c.is_eligible]
        assert len(eligible) > 0
        assert all(c.category is InformationCategory.CULTURE for c in eligible)
