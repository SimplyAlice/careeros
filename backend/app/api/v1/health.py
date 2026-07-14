"""Health check endpoint.

A minimal liveness check for this milestone: confirms the API process is
up and can respond. Deeper readiness checks (verifying DB and Redis are
actually reachable, per `docs/architecture/observability.md`) are a
natural extension once real repositories exist — introducing them now,
before there's anything meaningful to check, would be premature.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Shape of the health check response."""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return a simple liveness signal.

    Used by Docker Compose / Azure App Service health probes (see
    `docs/architecture/deployment-architecture.md`) to determine whether
    this instance should keep receiving traffic.
    """
    return HealthResponse(status="ok", service=settings.project_name, version=settings.version)
