from decimal import Decimal

import pytest

from app.domain.entities.planning.information import Activity, InformationCategory, InformationSource, Place


def test_place_and_activity_accept_valid_planning_information() -> None:
    place = Place(name="Venue", location="Cape Town", category=InformationCategory.CULTURE, description="A venue.")
    activity = Activity(name="Visit", category=InformationCategory.CULTURE, description="A visit.",
                        cost=Decimal("20"), duration_minutes=45, place_id=place.id)

    assert activity.place_id == place.id


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: Place(name="", location="Cape Town", category=InformationCategory.FOOD, description="Venue"), "name"),
        (lambda: Place(name="Venue", location="Cape Town", category=InformationCategory.FOOD, description="Venue", price_from=Decimal("-1")), "price"),
        (lambda: Activity(name="Visit", category=InformationCategory.CULTURE, description="Activity", cost=Decimal("1"), duration_minutes=0), "duration"),
        (lambda: Activity(name="Visit", category=InformationCategory.CULTURE, description="Activity", cost=Decimal("-1"), duration_minutes=30), "cost"),
    ],
)
def test_information_entities_reject_invalid_data(factory, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


def test_information_source_requires_an_identifier() -> None:
    with pytest.raises(ValueError, match="source identifier"):
        InformationSource(data_source="   ", is_live=False)

    assert InformationSource(data_source="development_fixture", is_live=False).is_live is False
