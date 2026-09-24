from decimal import Decimal

import pytest

from app.application.planning.information import OptionSearchCriteria, PlanningInformationService
from app.domain.entities.planning.information import Activity, InformationCategory, InformationSource, Place


class FakeInformationProvider:
    def __init__(self) -> None:
        self.place_criteria: OptionSearchCriteria | None = None
        self.activity_criteria: OptionSearchCriteria | None = None

    @property
    def source(self) -> InformationSource:
        return InformationSource(data_source="test_source", is_live=True)

    async def find_places(self, criteria: OptionSearchCriteria) -> list[Place]:
        self.place_criteria = criteria
        return [Place(name="Test venue", location="Cape Town", category=InformationCategory.FOOD, description="Fixture")]

    async def find_activities(self, criteria: OptionSearchCriteria) -> list[Activity]:
        self.activity_criteria = criteria
        return [Activity(name="Test activity", category=InformationCategory.FOOD, description="Fixture", cost=Decimal("10"), duration_minutes=30)]


@pytest.mark.asyncio
async def test_information_service_delegates_criteria_to_provider() -> None:
    provider = FakeInformationProvider()
    service = PlanningInformationService(provider)
    criteria = OptionSearchCriteria(location="Cape Town", maximum_cost=Decimal("100"))

    places = await service.search_places(criteria)
    activities = await service.search_activities(criteria)

    assert provider.place_criteria == criteria
    assert provider.activity_criteria == criteria
    assert places[0].name == "Test venue"
    assert activities[0].name == "Test activity"


def test_information_service_exposes_provider_source_neutrally() -> None:
    service = PlanningInformationService(FakeInformationProvider())

    assert service.source == InformationSource(data_source="test_source", is_live=True)


def test_search_criteria_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Maximum cost"):
        OptionSearchCriteria(maximum_cost=Decimal("-1"))
