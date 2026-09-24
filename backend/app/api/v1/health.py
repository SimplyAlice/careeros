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
import redis.asyncio as redis
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.infrastructure.cache.redis import get_redis_pool
from app.infrastructure.db.session import get_engine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Shape of the health check response."""

    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Shape of the readiness check response."""

    status: str
    service: str
    version: str
    database: str
    alembic_head: str | None
    redis: str


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return a simple liveness signal.

    Used by Docker Compose / Azure App Service health probes (see
    `docs/architecture/deployment-architecture.md`) to determine whether
    this instance should keep receiving traffic.
    """
    return HealthResponse(status="ok", service=settings.project_name, version=settings.version)


@router.get("/health/ready", response_model=ReadinessResponse, summary="Readiness check")
async def readiness(settings: Annotated[Settings, Depends(get_settings)]) -> ReadinessResponse:
    """Return readiness status verifying DB, Alembic migration head, and Redis connectivity."""
    db_status = "error"
    alembic_head: str | None = None
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                alembic_head = result.scalar_one_or_none()
            except Exception:
                alembic_head = "unmigrated"
    except Exception as exc:
        db_status = f"error: {type(exc).__name__}"

    redis_status = "error"
    try:
        pool = get_redis_pool()
        client = redis.Redis(connection_pool=pool)
        if await client.ping():
            redis_status = "connected"
    except Exception as exc:
        redis_status = f"error: {type(exc).__name__}"

    overall_status = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"

    return ReadinessResponse(
        status=overall_status,
        service=settings.project_name,
        version=settings.version,
        database=db_status,
        alembic_head=alembic_head,
        redis=redis_status,
    )


class MigrateResponse(BaseModel):
    """Shape of the migration response."""

    success: bool
    output: str
    error: str | None


@router.post("/health/migrate", response_model=MigrateResponse, summary="Trigger database migrations")
async def trigger_migration() -> MigrateResponse:
    """Run Alembic migrations up to head against the connected database."""
    import os
    import subprocess
    import sys

    alembic_dir = "backend" if os.path.exists("backend/alembic.ini") else "."
    try:
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=alembic_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return MigrateResponse(
            success=res.returncode == 0,
            output=res.stdout,
            error=res.stderr if res.returncode != 0 else None,
        )
    except Exception as exc:
        return MigrateResponse(
            success=False,
            output="",
            error=str(exc),
        )
