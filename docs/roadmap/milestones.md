# Milestones

Each milestone ends in something that runs and can be demoed. We do not move
to the next milestone until you've confirmed the current one works.

| # | Milestone | Key Deliverable | Est. Time |
|---|---|---|---|
| 0 | Foundations | This docs set | Complete |
| 1 | Core backend skeleton | FastAPI + Postgres + JWT auth, running in Docker Compose, `/health` green, register/login working, first tests passing in CI | Complete |
| 2 | Database schema | Full SQLAlchemy models + Alembic migrations for all v1 tables | Complete |
| 3 | Job ingestion | Adzuna adapter pulling real jobs into `jobs`, dedup working, basic `/jobs` list endpoint | 3–4 days |
| 4 | AI scoring engine | `LLMProvider` abstraction + Anthropic adapter, `/matches` endpoint returns score + rationale for a real job | 4–5 days |
| 5 | Resume/cover letter generation | Master profile input, AI-generated tailored resume + cover letter, versioned and PDF-rendered | 5–7 days |
| 6 | React dashboard v1 | Auth flow, Job Matches page, Applications page, Resume Library — wired to real API | 5–7 days |
| 7 | Assisted browser automation | Playwright adapter for one portal (e.g. Greenhouse-hosted form), pre-fill + human-confirm gate | 5–7 days |
| 8 | Background workers & scheduling | Celery Beat scheduled ingestion/scoring, task retries, idempotency | 3–4 days |
| 9 | Memory & dedup | Application-history-aware scoring context, duplicate-application prevention enforced end-to-end | 2–3 days |
| 10 | Notifications | Email + Discord webhook notifications on key events | 2 days |
| 11 | CI/CD | Full GitHub Actions pipeline: lint, type-check, test, build, push to ACR | 2–3 days |
| 12 | Azure deployment | Bicep-provisioned infra, live staging environment, deploy-on-merge | 4–6 days |
| 13 | Analytics dashboard | Response/interview rate charts, trend views, powered by real historical data | 3–4 days |
| 14 | Security hardening & polish | Rate limiting, audit logging review, RBAC pass, final README + demo video | 3–4 days |

**Total estimate:** roughly 8–12 weeks at a steady part-time pace — intentionally realistic, not aspirational.

## What each milestone hand-off will contain

1. A short explanation of the objective and the "why" behind key decisions.
2. The specific files/folders being added or changed.
3. Any new DB migration.
4. The code itself, introduced incrementally.
5. Tests for the new functionality.
6. A README/docs update.
7. A suggested Conventional Commits message (e.g. `feat(auth): add JWT login and refresh flow`).
8. A definition of "done" for that milestone.

See `roadmap/project-plan.md` for Git workflow and milestone process conventions.
