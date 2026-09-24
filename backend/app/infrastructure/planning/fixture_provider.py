"""Deterministic, development-only Cape Town planning options.

This fixture catalog is intentionally small and is not live information.
It exists only to exercise filtering and future decision-engine behaviour.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.application.planning.information import OptionSearchCriteria
from app.application.planning.ports import PlanningInformationProvider
from app.domain.entities.planning.information import Activity, InformationCategory, InformationSource, Place

V_AND_A_ID = UUID("10000000-0000-0000-0000-000000000001")
COMPANY_GARDENS_ID = UUID("10000000-0000-0000-0000-000000000002")
BO_KAAP_ID = UUID("10000000-0000-0000-0000-000000000003")
KLOOF_STREET_ID = UUID("10000000-0000-0000-0000-000000000004")
WATERFRONT_GRILL_ID = UUID("10000000-0000-0000-0000-000000000005")


class CapeTownFixtureInformationProvider(PlanningInformationProvider):
    """A stable catalog suitable for local development and automated tests.

    This is explicitly development-only fixture data: `is_live` is always
    `False` and no network or external API calls are ever made.
    """

    _source = InformationSource(data_source="development_fixture", is_live=False)

    _places = (
        Place(id=V_AND_A_ID, name="Harbour Market Hall", location="Cape Town", category=InformationCategory.FOOD,
              description="Fixture waterfront food hall with casual dining options.", price_from=Decimal("90"),
              opening_hours="Daily 10:00-21:00", maximum_group_size=12),
        Place(id=COMPANY_GARDENS_ID, name="Company Gardens", location="Cape Town", category=InformationCategory.NATURE,
              description="Fixture central-city green space for a relaxed walk.", price_from=Decimal("0"),
              opening_hours="Daily 07:00-19:00"),
        Place(id=BO_KAAP_ID, name="Bo-Kaap Cultural Stop", location="Cape Town", category=InformationCategory.CULTURE,
              description="Fixture cultural neighbourhood stop with a guided-history option.", price_from=Decimal("120"),
              opening_hours="Tue-Sun 09:00-17:00", maximum_group_size=8),
        Place(id=KLOOF_STREET_ID, name="Kloof Street Roastery", location="Cape Town", category=InformationCategory.FOOD,
              description="Fixture cozy neighborhood cafe and coffee roastery with relaxed indoor seating.", price_from=Decimal("45"),
              opening_hours="Daily 07:00-18:00", maximum_group_size=4),
        Place(id=WATERFRONT_GRILL_ID, name="Grand Harbour Fine Dining", location="Cape Town", category=InformationCategory.FOOD,
              description="Fixture upscale fine dining waterfront steakhouse with formal dress code.", price_from=Decimal("480"),
              opening_hours="Daily 18:00-23:00", maximum_group_size=6),
    )
    _activities = (
        Activity(id=UUID("20000000-0000-0000-0000-000000000001"), place_id=V_AND_A_ID, name="Harbour food tasting",
                 location="Cape Town", category=InformationCategory.FOOD,
                 description="Fixture shared tasting activity at the waterfront.", cost=Decimal("180"), duration_minutes=90,
                 maximum_group_size=6, metadata={"booking": "not_required", "weather_sensitive": "false"}),
        Activity(id=UUID("20000000-0000-0000-0000-000000000002"), place_id=COMPANY_GARDENS_ID, name="Gardens walking loop",
                 location="Cape Town", category=InformationCategory.NATURE,
                 description="Fixture self-guided daytime walk.", cost=Decimal("0"), duration_minutes=60,
                 metadata={"booking": "not_required", "weather_sensitive": "true"}),
        Activity(id=UUID("20000000-0000-0000-0000-000000000003"), place_id=BO_KAAP_ID, name="Neighbourhood history walk",
                 location="Cape Town", category=InformationCategory.CULTURE,
                 description="Fixture small-group cultural walk.", cost=Decimal("150"), duration_minutes=75,
                 maximum_group_size=8, metadata={"booking": "recommended", "weather_sensitive": "true"}),
        Activity(id=UUID("20000000-0000-0000-0000-000000000004"), place_id=KLOOF_STREET_ID, name="Artisan coffee & pastry flight",
                 location="Cape Town", category=InformationCategory.FOOD,
                 description="Fixture relaxed indoor coffee tasting and pastry pairing.", cost=Decimal("75"), duration_minutes=45,
                 maximum_group_size=3, metadata={"booking": "not_required", "weather_sensitive": "false"}),
        Activity(id=UUID("20000000-0000-0000-0000-000000000005"), place_id=WATERFRONT_GRILL_ID, name="Chef tasting menu & wine pairing",
                 location="Cape Town", category=InformationCategory.FOOD,
                 description="Fixture luxury multi-course fine dining tasting menu.", cost=Decimal("650"), duration_minutes=120,
                 maximum_group_size=6, metadata={"booking": "required", "weather_sensitive": "false"}),
    )

    @property
    def source(self) -> InformationSource:
        return self._source

    async def find_places(self, criteria: OptionSearchCriteria) -> list[Place]:
        return [place for place in self._places if _matches_place(place, criteria)]

    async def find_activities(self, criteria: OptionSearchCriteria) -> list[Activity]:
        return [activity for activity in self._activities if _matches_activity(activity, criteria)]

    async def get_place(self, place_id: UUID) -> Place | None:
        return next((place for place in self._places if place.id == place_id), None)

    async def get_activity(self, activity_id: UUID) -> Activity | None:
        return next((activity for activity in self._activities if activity.id == activity_id), None)


def _matches_place(place: Place, criteria: OptionSearchCriteria) -> bool:
    return (
        _matches_text(place.location, criteria.location)
        and (criteria.category is None or place.category is criteria.category)
        and (criteria.maximum_cost is None or place.price_from is None or place.price_from <= criteria.maximum_cost)
        and _supports_group(place.minimum_group_size, place.maximum_group_size, criteria.group_size)
    )


def _matches_activity(activity: Activity, criteria: OptionSearchCriteria) -> bool:
    return (
        _matches_text(activity.location, criteria.location)
        and (criteria.category is None or activity.category is criteria.category)
        and (criteria.maximum_cost is None or activity.cost <= criteria.maximum_cost)
        and (criteria.maximum_duration_minutes is None or activity.duration_minutes <= criteria.maximum_duration_minutes)
        and _supports_group(activity.minimum_group_size, activity.maximum_group_size, criteria.group_size)
    )


def _matches_text(value: str | None, expected: str | None) -> bool:
    return expected is None or (value is not None and value.casefold() == expected.strip().casefold())


def _supports_group(minimum: int, maximum: int | None, group_size: int | None) -> bool:
    return group_size is None or (group_size >= minimum and (maximum is None or group_size <= maximum))
