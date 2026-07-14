"""Shared FastAPI dependencies.

A single place for cross-cutting dependencies that route handlers will
`Depends()` on. Kept deliberately thin at this milestone — it re-exports
the settings/DB/Redis dependencies already defined in their owning
modules, so route handlers only need one import path
(`app.api.deps`) regardless of which infrastructure module actually
implements a dependency. Authentication dependencies (`get_current_user`,
`require_role`) are added here in the milestone that implements JWT auth.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.infrastructure.cache.redis import get_redis_client
from app.infrastructure.db.session import get_db_session

__all__ = [
    "Settings",
    "get_settings",
    "get_db_session",
    "get_redis_client",
]
