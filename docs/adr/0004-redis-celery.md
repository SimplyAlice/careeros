# ADR-0004: Use Redis + Celery for Background Task Processing

## Status
Accepted

## Context
Job ingestion, AI scoring/generation, and browser automation all take
anywhere from seconds to minutes, involve unreliable external dependencies
(third-party APIs, LLM providers, live websites), and must not block API
request threads.

## Decision
Use Celery as the task queue, with Redis as both the message broker and
result backend. Use Celery Beat for scheduled tasks (periodic job ingestion).

## Alternatives Considered
- **arq** (async-native Python task queue) — lighter weight and a more
  natural fit for an already-async FastAPI codebase, but Celery's maturity,
  documentation depth, and ecosystem (retries, rate limiting, Beat scheduling,
  monitoring via Flower) reduce risk for a project where the task
  orchestration itself needs to be demonstrably solid, not just functional.
  "Why Celery over arq" is itself treated as a good interview discussion
  point, not a settled non-issue.
- **RabbitMQ** as the broker instead of Redis — stronger delivery guarantees
  and queue semantics, but adds an additional infrastructure service to run
  and pay for. Redis's weaker guarantees are acceptable at this scale, given
  that tasks are also designed to be idempotent (see the reliability section
  of `architecture/cloud-architecture.md`).

## Consequences
- One additional piece of infrastructure (Redis) serves double duty as both
  cache and broker — appropriate at current scale; documented as a future
  split if either role's load grows enough to cause contention.
- Celery's synchronous worker process model is heavier than an async-native
  alternative — acceptable trade for ecosystem maturity and lower
  implementation risk.
- All tasks are designed to be idempotent and retry-safe from the start,
  since Redis-backed delivery does not guarantee exactly-once execution.
