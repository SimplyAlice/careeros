# CareerOS — Repository Folder Structure

```
careeros/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
├── backend/
│   ├── app/
│   │   ├── domain/                # entities, value objects, business rules
│   │   │   ├── entities/
│   │   │   └── value_objects/
│   │   ├── application/           # use cases / services, no framework imports
│   │   │   ├── scoring/
│   │   │   ├── resumes/
│   │   │   ├── cover_letters/
│   │   │   ├── applications/
│   │   │   └── automation/
│   │   ├── infrastructure/        # adapters
│   │   │   ├── db/
│   │   │   │   ├── models/        # SQLAlchemy models
│   │   │   │   └── repositories/
│   │   │   ├── ai_providers/
│   │   │   │   ├── base.py
│   │   │   │   ├── anthropic_provider.py
│   │   │   │   └── openai_provider.py
│   │   │   ├── job_sources/
│   │   │   │   ├── adzuna.py
│   │   │   │   └── greenhouse.py
│   │   │   ├── automation/
│   │   │   │   └── portals/
│   │   │   ├── storage/           # Azure Blob adapter
│   │   │   └── notifications/     # email, discord adapters
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── jobs.py
│   │   │   │   ├── applications.py
│   │   │   │   ├── resumes.py
│   │   │   │   └── analytics.py
│   │   │   └── deps.py            # shared FastAPI dependencies (auth, db session)
│   │   ├── workers/                # Celery task definitions
│   │   ├── core/                   # config, security utils, logging setup
│   │   └── main.py
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/                    # typed API client
│   │   ├── hooks/
│   │   ├── store/
│   │   └── types/
│   ├── tests/
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── bicep/
│   │   ├── main.bicep
│   │   ├── app-service.bicep
│   │   ├── postgres.bicep
│   │   ├── redis.bicep
│   │   ├── storage.bicep
│   │   └── key-vault.bicep
│   └── environments/
│       ├── dev.parameters.json
│       └── prod.parameters.json
├── docs/
│   ├── adr/
│   ├── 01-product-vision.md
│   ├── 02-architecture.md
│   ├── 03-tech-stack.md
│   ├── 04-database-design.md
│   ├── 05-strategies.md
│   ├── 06-cloud-security-observability.md
│   ├── 07-folder-structure.md
│   ├── 08-roadmap.md
│   └── 09-risks.md
├── docker-compose.yml
├── docker-compose.override.yml     # local dev overrides (hot reload, exposed ports)
├── .env.example
├── .gitignore
└── README.md
```

## Rationale

- `domain/` and `application/` never import from `infrastructure/` or `api/` —
  enforced by convention now, can be enforced by an import-linter rule later if
  the codebase grows enough to justify it.
- Each `infrastructure/` subfolder is an adapter category (db, ai_providers,
  job_sources, automation, storage, notifications) — adding a new AI provider
  or job source means adding one file in the matching folder, not touching
  anything else.
- `workers/` is deliberately thin — tasks call into `application/` services,
  they don't contain business logic themselves. This keeps business logic
  testable without spinning up Celery/Redis in unit tests.
- Backend and frontend are siblings with independent CI workflows and
  Dockerfiles, but share the repo so the whole system deploys from one
  source of truth — appropriate at this scale (a monorepo split into
  services later is a documented future option, not a day-one requirement).
