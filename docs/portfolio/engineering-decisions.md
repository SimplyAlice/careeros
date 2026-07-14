# Key Engineering Decisions

This page is written for a reader (recruiter, hiring manager, engineer)
skimming for evidence of judgment, not just a list of technologies used. Each
item below links to the full ADR for depth.

## 1. Human-in-the-loop over full automation
The original brief called for a fully autonomous auto-apply bot. That was
deliberately redesigned around a human-confirmation checkpoint before any
irreversible action, because job boards' Terms of Service prohibit automated
account activity, and a system that silently acts under a real user's
identity is both an account-ban risk and a weaker engineering story than one
that demonstrates judgment about automation risk. → `adr/0009-human-in-the-loop-automation.md`

## 2. Provider-agnostic AI layer instead of a hardcoded SDK call
Business logic (scoring, resume tailoring, cover letters) depends on a small
`LLMProvider` protocol, not a specific vendor SDK. Adding a new provider means
writing one adapter — not touching any service that uses it. → `adr/0005-ai-provider-abstraction.md`

## 3. Queue-backed background workers, not synchronous request handling
AI calls and browser automation take seconds to minutes and depend on
unreliable external services. Rather than blocking API request threads (and
timing out the frontend), this work is pushed to Celery workers behind
Redis, with idempotent task design so retries are safe. → `adr/0004-redis-celery.md`

## 4. Database-enforced duplicate-application prevention
"Don't apply to the same job twice" isn't just an application-code check — a
`(user_id, job_id)` unique constraint at the database level guarantees it
holds even under concurrent requests, which application logic alone cannot
guarantee.

## 5. Immutable resume versions
Once a resume version is generated and used in an application, it's never
mutated — if the user's master profile changes later, the historical
`Application` record still shows exactly what was actually sent to that
employer. This mirrors how real ATS systems (Greenhouse, Lever) version
documents, and it's a real requirement, not just defensive engineering.

## 6. Scoped module boundaries (pragmatic Clean Architecture)
`domain/` and `application/` code never imports from `infrastructure/` or
`api/`. This is applied specifically at the boundaries that actually change
over the project's life (database, AI provider, job source, automation
target) — not layered everywhere as a matter of dogma. The goal is a codebase
that's easy to test and easy to extend, not maximal architectural purity for
its own sake.

## 7. Deliberate, documented scope cuts
10 dashboard pages, 5 notification channels, and 6+ job boards were all in the
original brief. All are still on the roadmap — but sequenced, not
parallelized, because the biggest risk to a project this size is stalling at
"60% done across everything" instead of shipping a strong, complete core
first. See `roadmap/risks.md` for the full reasoning.

## 8. Everything reproducible from code
Infrastructure (Bicep), database schema (Alembic migrations), and CI/CD
(GitHub Actions) are all version-controlled. No environment depends on an
undocumented manual setup step — a deliberate choice for disaster-recovery
credibility and for demonstrating real operational discipline, not just
feature delivery.
