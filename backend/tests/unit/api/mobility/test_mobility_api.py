from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_get_mobility_providers_endpoint(client: AsyncClient) -> None:
    settings = get_settings()
    response = await client.get(f"{settings.api_v1_prefix}/mobility/providers")

    assert response.status_code == 200
    providers = response.json()
    assert isinstance(providers, list)
    assert len(providers) >= 6

    provider_ids = [p["provider_id"] for p in providers]
    assert "walking" in provider_ids
    assert "myciti" in provider_ids
    assert "prasa_metrorail" in provider_ids
    assert "golden_arrow" in provider_ids
    assert "uber" in provider_ids
    assert "bolt" in provider_ids
    assert "indrive" in provider_ids

    # Verify truthful declarations
    myciti = next(p for p in providers if p["provider_id"] == "myciti")
    assert myciti["has_realtime"] is False
    assert myciti["has_timetable"] is True

    uber = next(p for p in providers if p["provider_id"] == "uber")
    assert uber["booking_capability"] == "deeplink"


@pytest.mark.asyncio
async def test_post_mobility_options_endpoint(client: AsyncClient) -> None:
    settings = get_settings()
    payload = {
        "origin": "Kloof Street",
        "destination": "V&A Waterfront",
        "party_size": 2,
    }
    response = await client.post(f"{settings.api_v1_prefix}/mobility/options", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "options" in data
    assert data["total_options"] >= 2
    assert "query_summary" in data

    options = data["options"]
    modes = [opt["mode"] for opt in options]
    assert "walk" in modes
    assert "ride_hail" in modes

    # Verify Uber option has deeplink and unknown cost
    uber_opts = [opt for opt in options if opt["provider_id"] == "uber"]
    assert len(uber_opts) >= 1
    assert uber_opts[0]["booking_capability"] == "deeplink"
    assert uber_opts[0]["cost"] is None
    assert uber_opts[0]["cost_is_unknown"] is True
    assert "m.uber.com/ul/" in uber_opts[0]["booking_url"]

    # Verify walking option has R0 cost
    walk_opts = [opt for opt in options if opt["provider_id"] == "walking"]
    assert len(walk_opts) >= 1
    assert walk_opts[0]["cost"] == "0"
    assert walk_opts[0]["cost_is_unknown"] is False


@pytest.mark.asyncio
async def test_post_mobility_options_validation_error(client: AsyncClient) -> None:
    settings = get_settings()
    # Missing destination
    payload = {
        "origin": "Kloof Street",
        "destination": "",
    }
    response = await client.post(f"{settings.api_v1_prefix}/mobility/options", json=payload)
    assert response.status_code == 422
