# Tech Stack & Justifications

| Layer | Choice | Why | Main Alternative | Trade-off |
|---|---|---|---|---|
| API framework | **FastAPI** | Async-native, automatic OpenAPI docs, Pydantic validation | Django REST Framework | Loses built-in admin panel; gains async-first design |
| ORM | **SQLAlchemy 2.0 (async)** | Framework-independent, explicit query building, pairs with Alembic | Django ORM | More boilerplate, but decoupled from any web framework |
| Database | **PostgreSQL** | Relational integrity for a genuinely relational domain; JSONB for AI outputs | MongoDB | Weaker fit for this domain's relationships, not chosen |
| Cache/broker | **Redis** | Standard Celery broker; doubles as cache; managed Azure offering | RabbitMQ | Weaker delivery guarantees, mitigated by idempotent tasks |
| Task queue | **Celery** | Mature ecosystem, Beat scheduling, strong documentation | arq | Heavier process model, chosen for ecosystem maturity |
| AI providers | **Anthropic (primary)**, provider-agnostic interface | Strong structured-output following; swappable by design | Single hardcoded provider | Slight upfront abstraction cost for long-term flexibility |
| Browser automation | **Playwright** | Modern auto-wait semantics, deterministic, debuggable | Browser Use / Stagehand | Less "adaptive" to UI changes, more deterministic — matches the human-confirm-gate design |
| Frontend | **React + TypeScript + Vite** | Industry standard, fast dev loop, typed end-to-end | Next.js | No SSR — irrelevant for an authenticated dashboard |
| Styling | **Tailwind CSS** | Fast to build a distinctive, non-templated UI | CSS Modules | More verbose utility classes, mitigated with component extraction |
| Auth | **JWT (access + refresh)** | Stateless-friendly, horizontally scalable, revocable via server-side list | Session cookies | Requires careful refresh-token handling (see `adr/0008-jwt-auth.md`) |
| Containerization | **Docker + Docker Compose** | Reproducible dev, identical artifact dev-to-prod | Bare venv-only dev | None significant |
| CI/CD | **GitHub Actions** | Free for public repos, broad recruiter recognition | Azure DevOps Pipelines | Less "Microsoft-native," more broadly recognized |
| Cloud provider | **Microsoft Azure** | Explicit career-direction alignment; coherent managed-services story | AWS/GCP | None — a deliberate alignment choice |
| IaC | **Bicep** | Azure-native, no state file to manage | Terraform | Less portable across clouds; documented future stretch goal |
| Secrets | **Azure Key Vault** + managed identity | No stored access keys; secrets never in app config | App Service Configuration directly | Slightly more setup complexity |
| Observability | **Application Insights + structlog** | Native Azure integration, distributed tracing, low ops overhead | ELK stack | Less flexible, appropriately scoped for project size |
| Testing | **pytest** / **Vitest + RTL** | Standard, CI-friendly, fast (Vitest via Vite) | unittest / Jest | None significant |

## The Guiding Principle

Every "boring" choice here (Postgres over Mongo, Celery over rolling custom
async workers, JWT over hand-built tokens) is deliberate: production systems
are judged on operability and maintainability, not novelty. The differentiated
engineering effort goes into the **AI provider abstraction**, the
**human-in-the-loop automation gate**, and the **Azure deployment/
observability pipeline** — everywhere else, well-trodden, reliable tools are
used on purpose.

Full reasoning per decision, including rejected alternatives and consequences,
is in `docs/adr/`.
