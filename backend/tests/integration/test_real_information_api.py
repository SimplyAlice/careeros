"""API-level integration tests for real-world planning information (Milestone 3).

Verifies the integration between the API layer, OpenStreetMap provider,
verified real-world Cape Town catalog, and the planning decision engine.
"""

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
async def real_info_client(db_session: AsyncSession):
    app = create_app()

    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    # Uses default get_planning_information_provider (OpenStreetMapInformationProvider)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


async def _access_token(client: AsyncClient, email: str = "real_info@example.com") -> str:
    reg = await client.post(
        _prefix("auth/register"),
        json={"email": email, "password": "Sup3rSecretPassword123"},
    )
    assert reg.status_code == 201
    login = await client.post(
        _prefix("auth/login"),
        json={"email": email, "password": "Sup3rSecretPassword123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_real_information_recommendations_have_addresses_and_attribution(
    real_info_client: AsyncClient,
) -> None:
    token = await _access_token(real_info_client, "real_recs@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await real_info_client.get(
        _prefix("planning/options/recommendations"),
        headers=headers,
        params={"location": "Cape Town", "category": "culture"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["data_source"] == "openstreetmap"
    assert "OpenStreetMap" in body.get("attribution", "")
    assert len(body["candidates"]) > 0

    candidate = body["candidates"][0]
    assert candidate["address"] is not None
    assert len(candidate["address"]) > 0
    assert candidate["freshness"] in {"live", "recently_verified"}
    assert candidate["attribution"] == "© OpenStreetMap contributors"


@pytest.mark.asyncio
async def test_select_real_world_venue_into_plan(
    real_info_client: AsyncClient,
) -> None:
    token = await _access_token(real_info_client, "real_select@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a plan
    create_res = await real_info_client.post(
        _prefix("planning/plans"),
        headers=headers,
        json={"intention": "Saturday in town with friends", "location": "Cape Town", "group_size": 2},
    )
    assert create_res.status_code == 201
    plan_id = create_res.json()["id"]

    # 2. Get recommendations for the plan
    recs_res = await real_info_client.get(
        _prefix(f"planning/plans/{plan_id}/recommendations"),
        headers=headers,
    )
    assert recs_res.status_code == 200
    candidates = recs_res.json()["candidates"]
    assert len(candidates) > 0

    top = candidates[0]

    # 3. Add to plan from real-world option
    add_res = await real_info_client.post(
        _prefix(f"planning/plans/{plan_id}/items/from-option"),
        headers=headers,
        json={"option_id": top["option_id"], "option_type": top["option_type"]},
    )
    assert add_res.status_code == 201
    item = add_res.json()
    assert item["name"] == top["name"]
    # Location should reflect real address/suburb
    assert top["address"] in item["location"] or item["location"] in top["address"] or "Cape Town" in item["location"]


@pytest.mark.asyncio
async def test_real_world_options_places_and_activities(
    real_info_client: AsyncClient,
) -> None:
    token = await _access_token(real_info_client, "real_options@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Activities
    act_res = await real_info_client.get(
        _prefix("planning/options/activities"),
        headers=headers,
        params={"category": "culture"},
    )
    assert act_res.status_code == 200
    act_data = act_res.json()
    assert act_data["data_source"] == "openstreetmap"
    assert len(act_data["items"]) > 0
    assert any("Zeitz" in item["name"] or "Bo-Kaap" in item["name"] for item in act_data["items"])

    # Places
    place_res = await real_info_client.get(
        _prefix("planning/options/places"),
        headers=headers,
        params={"category": "food"},
    )
    assert place_res.status_code == 200
    place_data = place_res.json()
    assert place_data["data_source"] == "openstreetmap"
    assert len(place_data["items"]) > 0
    assert any("Kloof Street" in item["name"] or "Maria's" in item["name"] for item in place_data["items"])
