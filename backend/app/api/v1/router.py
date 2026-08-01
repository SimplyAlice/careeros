"""Aggregates all API v1 routers into a single router mounted by `app.main`.

As new resource routers are added (jobs, applications, resumes, ... in
later milestones), they're included here — `app.main` only ever needs to
know about this one router, not every individual endpoint module.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, cover_letters, health, jobs, matches, profile, resumes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(profile.router)
api_router.include_router(matches.router)
api_router.include_router(resumes.router)
api_router.include_router(cover_letters.router)
