from decimal import Decimal

import pytest

from app.application.planning.decision_service import PlanningDecisionService
from app.application.planning.information import OptionSearchCriteria, PlanningInformationService
from app.domain.entities.planning.decision import DecisionCriteria, ReasonOutcome, ReasonType
from app.domain.entities.planning.information import Activity, InformationCategory, InformationSource, Place


class FakeProvider:
    def __init__(self, places, activities) -> None:
        self._places = places
        self._activities = activities
        self.received: OptionSearchCriteria | None = None

    @property
    def source(self) -> InformationSource:
        return InformationSource(data_source="fake_source", is_live=False)

    async def find_places(self, criteria: OptionSearchCriteria) -> list[Place]:
        return list(self._places)

    async def find_activities(self, criteria: OptionSearchCriteria) -> list[Activity]:
        self.received = criteria
        return list(self._activities)


def _place(name="Venue", category=InformationCategory.FOOD, price=Decimal("100"), maximum_group_size=10):
    return Place(name=name, location="Cape Town", category=category, description="Fixture",
                 price_from=price, maximum_group_size=maximum_group_size)


def _activity(name="Tasting", category=InformationCategory.FOOD, cost=Decimal("150"), duration=60,
              maximum_group_size=6):
    return Activity(name=name, category=category, description="Fixture", cost=cost, duration_minutes=duration,
                    location="Cape Town", maximum_group_size=maximum_group_size)


def _service(places=None, activities=None) -> tuple[PlanningDecisionService, FakeProvider]:
    provider = FakeProvider(places or [], activities or [])
    return PlanningDecisionService(PlanningInformationService(provider)), provider


@pytest.mark.asyncio
async def test_recommend_orders_matching_option_first() -> None:
    service, _ = _service(places=[_place(name="Food hall")], activities=[_activity(name="Nature walk", category=InformationCategory.NATURE)])
    result = await service.recommend(DecisionCriteria(category=InformationCategory.FOOD, maximum_cost=Decimal("500")))

    assert result.candidates[0].name == "Food hall"
    assert result.candidates[0].is_eligible is True


@pytest.mark.asyncio
async def test_recommend_pushes_down_only_location_and_category_to_provider() -> None:
    service, provider = _service(activities=[_activity()])
    await service.recommend(DecisionCriteria(location="Cape Town", maximum_cost=Decimal("200"), group_size=3))

    # Only the narrowing filters reach the provider; the engine keeps budget
    # and group evaluation so it can explain exclusions.
    assert provider.received == OptionSearchCriteria(location="Cape Town")
    assert provider.received.maximum_cost is None
    assert provider.received.group_size is None


@pytest.mark.asyncio
async def test_recommend_marks_over_budget_option_ineligible() -> None:
    service, _ = _service(activities=[_activity(name="Pricey", cost=Decimal("900"))])
    result = await service.recommend(DecisionCriteria(maximum_cost=Decimal("500")))

    candidate = result.candidates[0]
    assert candidate.is_eligible is False
    assert next(r for r in candidate.reasons if r.type is ReasonType.BUDGET).outcome is ReasonOutcome.VIOLATED


@pytest.mark.asyncio
async def test_recommend_uses_information_source_as_provenance() -> None:
    service, _ = _service(activities=[_activity()])
    result = await service.recommend(DecisionCriteria())

    assert result.source == "fake_source"


@pytest.mark.asyncio
async def test_recommend_returns_empty_result_using_source_when_no_options() -> None:
    service, _ = _service()
    result = await service.recommend(DecisionCriteria())

    assert result.candidates == ()
    assert result.source == "fake_source"
