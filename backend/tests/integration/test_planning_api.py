"""API-level integration tests for intelligent planning."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.main import create_app


def _prefix(resource: str) -> str:
    return f"{get_settings().api_v1_prefix}/{resource}"


@pytest.fixture
async def planning_client(db_session: AsyncSession):
    app = create_app()

    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_create_plan_from_natural_language_request(
    planning_client: AsyncClient,
) -> None:
    register_response = await planning_client.post(
        _prefix("auth/register"),
        json={
            "email": "planner@example.com",
            "password": "Sup3rSecret",
        },
    )
    assert register_response.status_code == 201

    login_response = await planning_client.post(
        _prefix("auth/login"),
        json={
            "email": "planner@example.com",
            "password": "Sup3rSecret",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = await planning_client.post(
        _prefix("planning/requests"),
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "request": (
                "I want a fun Saturday with 3 friends, "
                "R800 total, somewhere in Cape Town."
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["intention"] == (
        "I want a fun Saturday with 3 friends, "
        "R800 total, somewhere in Cape Town."
    )
    assert body["status"]
    assert body["id"]


async def _access_token(client: AsyncClient, email: str) -> str:
    response = await client.post(_prefix("auth/register"), json={"email": email, "password": "Sup3rSecret"})
    assert response.status_code == 201
    response = await client.post(_prefix("auth/login"), json={"email": email, "password": "Sup3rSecret"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_authenticated_plan_crud_items_and_budget(planning_client: AsyncClient) -> None:
    token = await _access_token(planning_client, "aggregate@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    create = await planning_client.post(
        _prefix("planning/plans"), headers=headers,
        json={"intention": "Saturday in Cape Town", "title": "Saturday", "location": "Cape Town",
              "group_size": 2, "constraints": [{"type": "budget_max", "value": "R300", "numeric_value": "300"}]},
    )
    assert create.status_code == 201
    plan = create.json()
    plan_id = plan["id"]
    assert plan["context"]["group_size"] == 2
    assert plan["budget"]["remaining_budget"] == "300"

    item = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items"), headers=headers,
        json={"name": "Dinner", "item_type": "food", "estimated_cost": "350", "position": 3,
              "start_time": "2026-09-26T18:00:00Z", "end_time": "2026-09-26T19:30:00Z"},
    )
    assert item.status_code == 201
    item_id = item.json()["id"]
    assert item.json()["duration_minutes"] == 90

    detail = await planning_client.get(_prefix(f"planning/plans/{plan_id}"), headers=headers)
    assert detail.status_code == 200
    assert detail.json()["budget"]["total_planned_cost"] == "350.00"
    assert detail.json()["budget"]["remaining_budget"] == "-50.00"
    assert detail.json()["budget"]["is_over_budget"] is True

    updated = await planning_client.patch(
        _prefix(f"planning/plans/{plan_id}"), headers=headers,
        json={"title": "Updated Saturday", "status": "ready", "context": {"location": "CBD", "group_size": 3}},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Saturday"
    assert updated.json()["status"] == "ready"
    assert updated.json()["context"]["location"] == "CBD"

    updated_item = await planning_client.patch(
        _prefix(f"planning/plans/{plan_id}/items/{item_id}"), headers=headers,
        json={"estimated_cost": "250", "position": 1},
    )
    assert updated_item.status_code == 200
    assert updated_item.json()["position"] == 1

    listed = await planning_client.get(_prefix(f"planning/plans/{plan_id}/items"), headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["estimated_cost"] == "250.00"

    assert (await planning_client.delete(_prefix(f"planning/plans/{plan_id}/items/{item_id}"), headers=headers)).status_code == 204
    assert (await planning_client.delete(_prefix(f"planning/plans/{plan_id}"), headers=headers)).status_code == 204
    assert (await planning_client.get(_prefix(f"planning/plans/{plan_id}"), headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_plans_are_private_and_invalid_cost_is_rejected(planning_client: AsyncClient) -> None:
    owner_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'owner@example.com')}"}
    other_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'other@example.com')}"}
    created = await planning_client.post(_prefix("planning/plans"), headers=owner_headers, json={"intention": "Private plan"})
    plan_id = created.json()["id"]

    assert (await planning_client.get(_prefix(f"planning/plans/{plan_id}"), headers=other_headers)).status_code == 404
    assert (await planning_client.patch(_prefix(f"planning/plans/{plan_id}"), headers=other_headers,
                                               json={"title": "Nope"})).status_code == 404
    assert (await planning_client.delete(_prefix(f"planning/plans/{plan_id}"), headers=other_headers)).status_code == 404
    invalid_cost = await planning_client.post(_prefix(f"planning/plans/{plan_id}/items"), headers=owner_headers,
                                              json={"name": "Bad", "item_type": "food", "estimated_cost": "-1"})
    assert invalid_cost.status_code == 422
    assert (await planning_client.get(_prefix("planning/plans"))).status_code == 403


@pytest.mark.asyncio
async def test_planning_information_options_are_authenticated_filtered_fixture_data(
    planning_client: AsyncClient,
) -> None:
    headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'information@example.com')}"}

    activities = await planning_client.get(
        _prefix("planning/options/activities"), headers=headers,
        params={"location": "Cape Town", "category": "culture", "maximum_cost": "200", "group_size": 4,
                "maximum_duration_minutes": 90},
    )
    assert activities.status_code == 200
    activity_body = activities.json()
    assert activity_body["data_source"] == "development_fixture"
    assert activity_body["is_live"] is False
    assert [item["name"] for item in activity_body["items"]] == ["Neighbourhood history walk"]

    places = await planning_client.get(
        _prefix("planning/options/places"), headers=headers,
        params={"maximum_cost": "100", "group_size": 10},
    )
    assert places.status_code == 200
    assert [item["name"] for item in places.json()["items"]] == ["Harbour Market Hall", "Company Gardens"]

    assert (await planning_client.get(_prefix("planning/options/places"))).status_code == 403


@pytest.mark.asyncio
async def test_planning_recommendations_are_authenticated_ordered_and_explained(
    planning_client: AsyncClient,
) -> None:
    headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'recommend@example.com')}"}

    response = await planning_client.get(
        _prefix("planning/options/recommendations"), headers=headers,
        params={"location": "Cape Town", "category": "culture", "maximum_cost": "200", "group_size": 4,
                "maximum_duration_minutes": 90},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data_source"] == "development_fixture"
    assert body["is_live"] is False
    assert [c["name"] for c in body["candidates"]] == ["Neighbourhood history walk", "Bo-Kaap Cultural Stop"]

    top = body["candidates"][0]
    assert top["option_type"] == "activity"
    assert top["is_eligible"] is True
    assert top["score"] > 0
    reason_types = {reason["type"] for reason in top["reasons"]}
    assert {"category", "budget", "group_size", "duration"} <= reason_types

    over_budget = await planning_client.get(
        _prefix("planning/options/recommendations"), headers=headers,
        params={"category": "culture", "maximum_cost": "10"},
    )
    assert over_budget.status_code == 200
    candidates = over_budget.json()["candidates"]
    assert candidates
    assert all(candidate["is_eligible"] is False for candidate in candidates)
    assert any(r["outcome"] == "violated" and r["type"] == "budget" for r in candidates[0]["reasons"])

    assert (await planning_client.get(_prefix("planning/options/recommendations"))).status_code == 403


HARBOUR_MARKET_PLACE_ID = "10000000-0000-0000-0000-000000000001"
HISTORY_WALK_ACTIVITY_ID = "20000000-0000-0000-0000-000000000003"


@pytest.mark.asyncio
async def test_select_option_adds_authoritative_plan_item_and_updates_budget(
    planning_client: AsyncClient,
) -> None:
    headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'select@example.com')}"}
    created = await planning_client.post(
        _prefix("planning/plans"), headers=headers,
        json={"intention": "Saturday in Cape Town", "location": "Cape Town", "group_size": 2,
              "constraints": [{"type": "budget_max", "value": "R300", "numeric_value": "300"}]},
    )
    plan_id = created.json()["id"]

    selected = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"), headers=headers,
        json={"option_id": HARBOUR_MARKET_PLACE_ID, "option_type": "place"},
    )
    assert selected.status_code == 201
    item = selected.json()
    # Authoritative server-side data — client never supplied name/cost/location.
    assert item["name"] == "Harbour Market Hall"
    assert item["item_type"] == "food"
    assert Decimal(item["estimated_cost"]) == Decimal("90")
    assert item["location"] == "Cape Town"
    assert item["position"] == 0

    detail = await planning_client.get(_prefix(f"planning/plans/{plan_id}"), headers=headers)
    assert detail.json()["budget"]["total_planned_cost"] == "90.00"
    assert detail.json()["budget"]["remaining_budget"] == "210.00"

    activity = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"), headers=headers,
        json={"option_id": HISTORY_WALK_ACTIVITY_ID, "option_type": "activity",
              "start_time": "2026-09-26T10:00:00Z"},
    )
    assert activity.status_code == 201
    assert activity.json()["name"] == "Neighbourhood history walk"
    assert activity.json()["position"] == 1
    assert activity.json()["duration_minutes"] == 75


@pytest.mark.asyncio
async def test_select_option_enforces_auth_ownership_and_valid_option(planning_client: AsyncClient) -> None:
    owner_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'select-owner@example.com')}"}
    other_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'select-other@example.com')}"}
    created = await planning_client.post(_prefix("planning/plans"), headers=owner_headers,
                                         json={"intention": "Private selection plan"})
    plan_id = created.json()["id"]

    # Authentication is required.
    assert (await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"),
        json={"option_id": HARBOUR_MARKET_PLACE_ID, "option_type": "place"},
    )).status_code == 403

    # Another user's plan is reported as not found, never as forbidden.
    foreign = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"), headers=other_headers,
        json={"option_id": HARBOUR_MARKET_PLACE_ID, "option_type": "place"},
    )
    assert foreign.status_code == 404

    # Unknown option id is rejected.
    unknown = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"), headers=owner_headers,
        json={"option_id": "99999999-0000-0000-0000-000000000000", "option_type": "place"},
    )
    assert unknown.status_code == 404

    # Unsupported option type is rejected by request validation.
    bad_type = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"), headers=owner_headers,
        json={"option_id": HARBOUR_MARKET_PLACE_ID, "option_type": "transport"},
    )
    assert bad_type.status_code == 422

    # Archived plans cannot receive selections.
    await planning_client.patch(_prefix(f"planning/plans/{plan_id}"), headers=owner_headers,
                                json={"status": "archived"})
    archived = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"), headers=owner_headers,
        json={"option_id": HARBOUR_MARKET_PLACE_ID, "option_type": "place"},
    )
    assert archived.status_code == 422


@pytest.mark.asyncio
async def test_archived_plan_and_item_deletion_is_rejected(
    planning_client: AsyncClient,
) -> None:
    owner_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'del-owner@example.com')}"}
    other_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'del-other@example.com')}"}

    created = await planning_client.post(
        _prefix("planning/plans"), headers=owner_headers,
        json={"intention": "Mutable then archived plan", "location": "Cape Town"},
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    item = await planning_client.post(
        _prefix(f"planning/plans/{plan_id}/items"), headers=owner_headers,
        json={"name": "Museum visit", "item_type": "activity", "estimated_cost": "120"},
    )
    assert item.status_code == 201
    item_id = item.json()["id"]

    # Archive the plan
    archive_res = await planning_client.patch(
        _prefix(f"planning/plans/{plan_id}"), headers=owner_headers,
        json={"status": "archived"},
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"

    # Attempt to delete item from archived plan is rejected with 422
    del_item = await planning_client.delete(
        _prefix(f"planning/plans/{plan_id}/items/{item_id}"), headers=owner_headers,
    )
    assert del_item.status_code == 422
    assert "Archived plans cannot be modified." in del_item.json()["detail"]

    # Attempt to delete archived plan itself is rejected with 422
    del_plan = await planning_client.delete(
        _prefix(f"planning/plans/{plan_id}"), headers=owner_headers,
    )
    assert del_plan.status_code == 422
    assert "Archived plans cannot be modified." in del_plan.json()["detail"]

    # Foreign user attempting to delete returns 404 (ownership isolation)
    del_foreign_item = await planning_client.delete(
        _prefix(f"planning/plans/{plan_id}/items/{item_id}"), headers=other_headers,
    )
    assert del_foreign_item.status_code == 404

    del_foreign_plan = await planning_client.delete(
        _prefix(f"planning/plans/{plan_id}"), headers=other_headers,
    )
    assert del_foreign_plan.status_code == 404


@pytest.mark.asyncio
async def test_plan_aware_recommendations_endpoint(
    planning_client: AsyncClient,
) -> None:
    owner_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'plan-rec-owner@example.com')}"}
    other_headers = {"Authorization": f"Bearer {await _access_token(planning_client, 'plan-rec-other@example.com')}"}

    # Create a plan with location, group_size, budget and preference category
    created = await planning_client.post(
        _prefix("planning/plans"), headers=owner_headers,
        json={
            "intention": "Cultural tour in Cape Town with 4 friends",
            "location": "Cape Town",
            "group_size": 4,
            "constraints": [
                {"type": "budget_max", "value": "R200", "numeric_value": "200"},
                {"type": "preference", "value": "culture"},
            ],
        },
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    # 1. Unauthenticated request rejected with 403
    unauth = await planning_client.get(_prefix(f"planning/plans/{plan_id}/recommendations"))
    assert unauth.status_code == 403

    # 2. Missing plan returns 404
    missing = await planning_client.get(
        _prefix("planning/plans/00000000-0000-0000-0000-000000000000/recommendations"),
        headers=owner_headers,
    )
    assert missing.status_code == 404

    # 3. Foreign user's plan returns 404
    foreign = await planning_client.get(
        _prefix(f"planning/plans/{plan_id}/recommendations"),
        headers=other_headers,
    )
    assert foreign.status_code == 404

    # 4. Authenticated owner retrieves plan-derived recommendations
    rec = await planning_client.get(
        _prefix(f"planning/plans/{plan_id}/recommendations"),
        headers=owner_headers,
    )
    assert rec.status_code == 200
    body = rec.json()

    # Verify structure matches RecommendationResponse
    assert body["data_source"] == "development_fixture"
    assert body["is_live"] is False
    assert len(body["candidates"]) > 0

    top = body["candidates"][0]
    assert top["name"] == "Neighbourhood history walk"
    assert top["category"] == "culture"
    assert top["location"] == "Cape Town"
    assert top["is_eligible"] is True
    assert top["score"] > 0
    reason_types = {r["type"] for r in top["reasons"]}
    assert {"location", "category", "budget", "group_size"} <= reason_types
