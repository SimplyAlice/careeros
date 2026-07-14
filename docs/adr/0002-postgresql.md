# ADR-0002: Use PostgreSQL as the Primary Database

## Status
Accepted

## Context
The domain is highly relational: a `User` has `Applications`, each
`Application` references a `Job`, a `Resume Version`, and optionally a `Cover
Letter`; duplicate-application prevention and audit history depend on
relational integrity and constraints, not just document flexibility.

## Decision
Use PostgreSQL, hosted via Azure Database for PostgreSQL — Flexible Server in
the cloud.

## Alternatives Considered
- **MongoDB** — flexible schema is appealing for AI-generated content, but
  the core domain (users → applications → jobs → resumes, with foreign-key
  integrity and a `(user_id, job_id)` uniqueness constraint) is a poor fit for
  a document database's strengths, and would require re-implementing
  relational guarantees in application code.
- **MySQL** — a reasonable alternative, but Postgres's native JSONB support
  (used for semi-structured resume content and AI rationale) and its more
  mature Azure-managed offering tip the decision.

## Consequences
- We get real foreign-key constraints and a database-enforced uniqueness
  constraint for duplicate-application prevention (FR-14) — this guarantee
  holds even under concurrent requests, which application-level checks alone
  cannot guarantee.
- JSONB columns give schema flexibility for AI-generated/semi-structured data
  (resume content, master profile) without giving up relational integrity
  everywhere else — the best of both models where each is actually needed.
- Requires Alembic-managed migrations as the schema evolves — an explicit,
  reviewable, versioned process rather than an implicit schema.
