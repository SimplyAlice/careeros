"""Tests for OpenStreetMapInformationProvider."""
from decimal import Decimal
from unittest.mock import patch
import urllib.error

import pytest

from app.application.planning.information import OptionSearchCriteria
from app.domain.entities.planning.information import (
    FreshnessKind,
    InformationCategory,
)
from app.infrastructure.planning.openstreetmap_provider import (
    OSM_ATTRIBUTION,
    PLACES_CATALOG,
    OpenStreetMapInformationProvider,
)


@pytest.fixture
def provider() -> OpenStreetMapInformationProvider:
    # Disable network for fast, deterministic unit test execution
    return OpenStreetMapInformationProvider(enable_network=False)


def test_provider_source_metadata(provider: OpenStreetMapInformationProvider) -> None:
    source = provider.source
    assert source.data_source == "openstreetmap"
    assert source.is_live is False
    assert source.attribution == OSM_ATTRIBUTION
    assert source.freshness == FreshnessKind.RECENTLY_VERIFIED


@pytest.mark.asyncio
async def test_find_places_all(provider: OpenStreetMapInformationProvider) -> None:
    criteria = OptionSearchCriteria(location="Cape Town")
    places = await provider.find_places(criteria)
    assert len(places) > 10
    for place in places:
        assert place.location == "Cape Town"
        assert place.source == "openstreetmap"
        assert place.address is not None
        assert place.freshness == FreshnessKind.RECENTLY_VERIFIED
        assert place.verified_at is not None


@pytest.mark.asyncio
async def test_find_places_by_category(provider: OpenStreetMapInformationProvider) -> None:
    criteria = OptionSearchCriteria(location="Cape Town", category=InformationCategory.NATURE)
    places = await provider.find_places(criteria)
    assert len(places) >= 4
    names = {p.name for p in places}
    assert "Kirstenbosch National Botanical Garden" in names
    assert "Table Mountain Aerial Cableway" in names
    assert "Sea Point Promenade" in names


@pytest.mark.asyncio
async def test_find_places_by_neighborhood(provider: OpenStreetMapInformationProvider) -> None:
    criteria = OptionSearchCriteria(location="Waterfront")
    places = await provider.find_places(criteria)
    assert len(places) >= 3
    names = {p.name for p in places}
    assert "Zeitz MOCAA" in names or "V&A Waterfront Food Market" in names


@pytest.mark.asyncio
async def test_find_places_by_budget(provider: OpenStreetMapInformationProvider) -> None:
    criteria = OptionSearchCriteria(location="Cape Town", maximum_cost=Decimal("70"))
    places = await provider.find_places(criteria)
    assert len(places) >= 4
    for p in places:
        assert p.price_from is None or p.price_from <= Decimal("70")


@pytest.mark.asyncio
async def test_find_places_by_group_size(provider: OpenStreetMapInformationProvider) -> None:
    criteria = OptionSearchCriteria(location="Cape Town", group_size=10)
    places = await provider.find_places(criteria)
    for p in places:
        assert p.minimum_group_size <= 10
        assert p.maximum_group_size is None or p.maximum_group_size >= 10


@pytest.mark.asyncio
async def test_find_activities(provider: OpenStreetMapInformationProvider) -> None:
    criteria = OptionSearchCriteria(location="Cape Town", category=InformationCategory.FOOD)
    activities = await provider.find_activities(criteria)
    assert len(activities) >= 4
    for a in activities:
        assert a.category is InformationCategory.FOOD
        assert a.source == "openstreetmap"
        assert a.address is not None


@pytest.mark.asyncio
async def test_get_place_and_activity_by_id(provider: OpenStreetMapInformationProvider) -> None:
    first_place = PLACES_CATALOG[0]
    p = await provider.get_place(first_place.id)
    assert p is not None
    assert p.name == first_place.name

    a = await provider.get_activity(first_place.id)
    # The place id is not an activity id
    assert a is None


@pytest.mark.asyncio
async def test_live_network_fallback_on_error() -> None:
    # Test network failure gracefully falling back to catalog
    online_provider = OpenStreetMapInformationProvider(enable_network=True, timeout_seconds=0.5)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        places = await online_provider.find_places(OptionSearchCriteria(location="Camps Bay"))
        # Should gracefully return Camps Bay places from verified catalog without raising
        assert len(places) >= 1
        assert any("Camps Bay" in (p.address or "") for p in places)
