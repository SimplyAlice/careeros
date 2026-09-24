from decimal import Decimal

import pytest

from app.application.planning.information import OptionSearchCriteria
from app.domain.entities.planning.information import InformationCategory
from app.infrastructure.planning.fixture_provider import CapeTownFixtureInformationProvider


def test_fixture_provider_is_explicitly_non_live_development_fixture() -> None:
    provider = CapeTownFixtureInformationProvider()

    assert provider.source.data_source == "development_fixture"
    assert provider.source.is_live is False


@pytest.mark.asyncio
async def test_fixture_provider_returns_deterministic_cape_town_results() -> None:
    provider = CapeTownFixtureInformationProvider()
    criteria = OptionSearchCriteria(location="cape town")

    first = await provider.find_activities(criteria)
    second = await provider.find_activities(criteria)

    assert [item.id for item in first] == [item.id for item in second]
    assert all(item.source == "development_fixture" for item in first)


@pytest.mark.asyncio
async def test_fixture_provider_filters_activity_cost_group_and_duration() -> None:
    provider = CapeTownFixtureInformationProvider()
    results = await provider.find_activities(
        OptionSearchCriteria(category=InformationCategory.FOOD, maximum_cost=Decimal("200"),
                             group_size=4, maximum_duration_minutes=100)
    )

    assert [item.name for item in results] == ["Harbour food tasting"]

    # Activities with a bounded maximum group size are excluded; only the
    # unbounded fixture activity remains for an oversized group.
    oversized = await provider.find_activities(OptionSearchCriteria(group_size=10))
    assert [item.name for item in oversized] == ["Gardens walking loop"]


@pytest.mark.asyncio
async def test_fixture_provider_filters_places_by_cost_and_group() -> None:
    provider = CapeTownFixtureInformationProvider()

    results = await provider.find_places(OptionSearchCriteria(maximum_cost=Decimal("100"), group_size=10))

    assert [item.name for item in results] == ["Harbour Market Hall", "Company Gardens"]
