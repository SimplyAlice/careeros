# ADR-0001: Use FastAPI as the API Framework

## Status
Accepted

## Context
We need a Python web framework for a REST API that is async-friendly (many
downstream calls — DB, Redis, LLM providers — are I/O bound), strongly typed,
and produces good API documentation with minimal extra work.

## Decision
Use FastAPI.

## Alternatives Considered
- **Django + Django REST Framework** — mature, batteries-included (admin
  panel, ORM, auth scaffolding), but sync-first by default and heavier than
  needed for an API-only service with a separate React frontend.
- **Flask** — minimal and flexible, but async support and validation are
  bolt-ons rather than first-class, requiring more manual wiring for the same
  guarantees FastAPI gives out of the box.

## Consequences
- Pydantic models give request/response validation and typed schemas "for
  free," pairing well with a typed TypeScript frontend.
- We give up Django's built-in admin panel — acceptable, since an internal
  admin UI isn't a v1 requirement; a tool like SQLAdmin can fill that gap
  later if needed.
- Async-first design pushes naturally toward the Celery-based background
  worker architecture for anything slow (AI calls, browser automation) — the
  correct architecture regardless of framework choice, but FastAPI makes it
  the path of least resistance rather than something fought against.
