# Deployment Architecture

## 1. Deployment Topology

```mermaid
flowchart TB
    subgraph Edge
        CDN["Azure Front Door / Static Hosting\n(React build)"]
    end
    subgraph Compute
        AppSvc["Azure App Service\n(FastAPI container, from ACR)"]
        Workers["Container Apps\n(Celery workers)"]
    end
    subgraph Data
        PG[("Azure DB for PostgreSQL\nFlexible Server")]
        Redis[("Azure Cache for Redis")]
        Blob[("Azure Blob Storage")]
    end
    subgraph CrossCutting["Cross-Cutting"]
        KV["Azure Key Vault"]
        Monitor["Azure Monitor +\nApplication Insights"]
    end

    CDN --> AppSvc
    AppSvc --> PG
    AppSvc --> Redis
    AppSvc --> Blob
    AppSvc --> Workers
    Workers --> PG
    Workers --> Redis
    Workers --> Blob
    AppSvc -.secrets.-> KV
    Workers -.secrets.-> KV
    AppSvc -.telemetry.-> Monitor
    Workers -.telemetry.-> Monitor
```

## 2. CI/CD Pipeline

```mermaid
flowchart LR
    A["git push"] --> B["GitHub Actions triggered"]
    B --> C["Lint + type-check\n(ruff/mypy, eslint/tsc)"]
    C --> D["Run tests\n(pytest, vitest)"]
    D --> E["Build Docker image\ntag = git SHA"]
    E --> F["Push image to ACR"]
    F --> G{Branch?}
    G -->|main| H["Deploy to staging\n(auto)"]
    G -->|release tag| I["Deploy to prod\n(auto, on tag)"]
    H --> J["Run Alembic migrations"]
    I --> J
    J --> K["Smoke test /health"]
    K -->|pass| L["Deployment complete"]
    K -->|fail| M["Rollback to previous image tag"]
```

## 3. Environments

| Environment | Trigger | Purpose |
|---|---|---|
| **dev** | Local `docker-compose up` | Day-to-day development, hot reload |
| **staging** | Merge to `main` | Integration testing against real Azure services, pre-prod validation |
| **prod** | Tagged release (`v*`) | The live, demoable environment linked from the portfolio README |

Staging and prod use **separate Azure resource groups and separate Key
Vaults**, so a staging misconfiguration can never touch production secrets.

## 4. Rollback Strategy

- Container images are immutable and tagged by git SHA — rollback means
  redeploying the previous tag, not rebuilding.
- Database migrations are written to be backward-compatible for at least one
  release: additive changes (new nullable columns, new tables) ship first;
  destructive changes (dropping/renaming columns) ship in a following release
  once nothing references the old shape. This means a code rollback never
  requires an accompanying DB rollback.
- Smoke test (`/health` returning 200 post-deploy) gates whether a deploy is
  considered successful; a failed smoke test triggers an automatic redeploy of
  the last known-good image tag.

## 5. Scaling Path (documented, not implemented in v1)

| Trigger | Response |
|---|---|
| API CPU/memory consistently > 70% | Scale out App Service plan (more instances) — stateless API design (JWT, no server-side session) makes this a no-code change |
| Celery task queue depth growing faster than it drains | Scale out Container Apps worker replica count |
| Postgres connections saturating | Introduce PgBouncer connection pooling before vertically scaling the DB tier |
| Redis memory pressure from cache growth | Split cache and broker into separate Redis instances |

This table exists so scaling is a **documented, deliberate decision** made
when a real signal appears — not guessed at upfront (premature scaling adds
cost and complexity with no evidence it's needed yet).
