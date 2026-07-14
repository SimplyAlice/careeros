# Cloud Architecture (Azure)

This doc gets extra weight because cloud engineering is the explicit career
direction this project is built to demonstrate — every choice below is written
to be defensible in an interview, not just functional.

## 1. Service Selection

| Concern | Azure Service | Why |
|---|---|---|
| Container hosting (API) | **Azure App Service** (Web App for Containers) | Simplest managed compute for a containerized FastAPI app; scales without managing VMs; built-in deployment slots for zero-downtime releases |
| Container hosting (workers) | **Azure Container Apps** | Celery workers are long-running processes, not request/response — Container Apps' KEDA-based scaling fits queue-depth-driven scaling better than App Service |
| Image registry | **Azure Container Registry (ACR)** | Private registry; integrates with App Service/Container Apps via managed identity — no stored registry credentials anywhere |
| Database | **Azure Database for PostgreSQL — Flexible Server** | Managed backups, patching, HA options; Burstable tier keeps dev cost near-zero, same service scales to General Purpose in prod |
| Cache/broker | **Azure Cache for Redis** (Basic tier for dev) | Managed, low-ops; Basic tier has no SLA/replication — documented trade-off, upgrade path to Standard/Premium exists without code changes |
| Blob storage | **Azure Blob Storage** | Resume/cover letter PDFs, uploads; private containers, access via managed identity or short-lived SAS tokens, never public |
| Secrets | **Azure Key Vault** | App Service/Container Apps pull secrets via managed identity at runtime — no secrets in App Settings, no secrets baked into the image |
| Observability | **Application Insights + Azure Monitor** | Request tracing, dependency tracking, custom business metrics, alerting — native to the platform, no extra infra to run |
| IaC | **Bicep** | Native Azure syntax, no state file to manage (unlike Terraform), first-class support for what-if diffs before apply |

## 2. Scalability

- **Stateless API tier**: JWT auth means no server-side session store — any
  API instance can serve any request, so horizontal scaling (adding App
  Service instances) requires no code change.
- **Queue-based worker scaling**: Celery worker replica count scales off queue
  depth (Container Apps + KEDA), not CPU — the right signal for a system whose
  bottleneck is "how many pending AI/automation jobs are waiting," not raw
  compute.
- **Read-heavy dashboard traffic**: job listing and match endpoints are
  cacheable (Redis) since job data changes on an ingestion schedule, not
  per-request — reduces DB load under dashboard traffic spikes.

## 3. Reliability & Fault Tolerance

- **Idempotent tasks**: every Celery task is written so re-running it after a
  crash/retry produces the same end state (e.g. ingestion upserts by
  `(source, external_id)`, it doesn't blindly insert). This is what makes
  "retry on failure" actually safe.
- **Circuit-breaking on external dependencies**: LLM provider and job-source
  API calls use timeouts + bounded retries with exponential backoff; a
  persistent failure marks that specific task failed rather than retrying
  forever and starving the queue.
- **Graceful degradation**: if the AI provider is down, job ingestion and
  application tracking keep working — only scoring/generation pauses. The
  system is decomposed precisely so a single external dependency's outage
  doesn't cascade into the whole app being unusable.
- **Health checks**: `/health` (liveness) and `/health/ready` (readiness — DB
  and Redis reachable) let Azure's platform health probes and any future load
  balancer make correct routing/restart decisions.

## 4. Backup Strategy & Disaster Recovery

| Asset | Backup Approach | Recovery Objective (target, not SLA-guaranteed at this scale) |
|---|---|---|
| PostgreSQL | Automated daily backups (Azure managed, point-in-time restore within retention window) | RPO ~24h (or better, since Flexible Server supports continuous log backup for PITR); RTO: restore to new server, repoint App Service config |
| Blob Storage | Soft-delete + versioning enabled on containers | RPO near-zero for accidental deletes; protects against overwrite mistakes |
| Infrastructure | Bicep templates in git — the environment itself is reproducible from code | RTO for a full region loss: re-provision via `az deployment` against a new region, restore DB from latest backup |
| Secrets | Key Vault has its own soft-delete + purge protection | Prevents accidental permanent secret loss |

Disaster recovery for a solo portfolio project doesn't warrant multi-region
active-active — that would be over-engineering relative to real need. What it
does warrant, and what's implemented, is: **nothing is a manual, undocumented,
one-time setup step.** Every resource is provisionable from the Bicep
templates, so "the region went down" becomes "redeploy the IaC and restore the
DB backup," not "hope someone remembers how it was configured."

## 5. Secrets Management

- No secret ever committed to git — `.env` is gitignored from commit 1,
  `.env.example` ships with placeholder values only.
- Local dev: `.env` + `python-dotenv`.
- Cloud: Azure Key Vault, referenced by App Service/Container Apps via
  **managed identity** — the app never holds a Key Vault access key; Azure AD
  handles that trust relationship.
- CI: GitHub Actions secrets (encrypted, scoped to the repo) for
  deployment credentials (federated OIDC login to Azure preferred over a
  long-lived service principal secret, to avoid a static credential existing
  at all).

## 6. Monitoring, Logging, Metrics, Tracing

- **Logging**: structured JSON logs (`structlog`) with a consistent field set
  (request_id, user_id, task_name) so logs correlate across API and worker
  processes inside Application Insights.
- **Metrics**: infrastructure metrics (CPU, memory, request rate) plus
  business metrics emitted alongside them — jobs ingested/hour, applications
  submitted/day, automation success/failure rate, AI call latency and
  approximate token cost per call. This ties observability directly to what
  the Analytics dashboard shows the user.
- **Tracing**: Application Insights SDK auto-instruments FastAPI and outbound
  calls (DB, Redis, HTTP to LLM providers) — a slow request can be traced to
  "the Anthropic API call took 4.2s," not just "the request was slow."
- **Alerting**: Azure Monitor alert rules on error-rate spikes, health-check
  failures, and automation failure-rate — the useful signal here is "the
  Greenhouse adapter's failure rate just spiked," not just "something is
  slow."

Full detail lives in `architecture/observability.md` — this section exists
here specifically to tie observability to the cloud services that host it.

## 7. Performance Optimization

- Cache pre-computed job match scores; never recompute on page load.
- Paginate all list endpoints with cursor-based pagination (stable under
  concurrent inserts, unlike offset pagination).
- Async I/O throughout the API (FastAPI + async SQLAlchemy) so one slow
  downstream call doesn't block unrelated requests on the same process.
- PDF generation and AI calls are always backgrounded — never on the request
  path.

## 8. Cost Considerations

- Development/portfolio-demo footprint targets Azure free tier + student
  credits: Postgres Flexible Server Burstable (B1ms), Redis Basic, App Service
  Free/Basic tier, Blob Storage (pennies at this data volume).
- Bicep parameterization means dev/staging can run on minimal SKUs while prod
  parameters describe the "real" scale-up path — the same templates serve
  both, only parameters change.
- Since environments are fully reproducible from IaC, they don't need to run
  continuously — `az group delete` between work sessions is a legitimate,
  documented cost-control practice for a project without live production
  traffic, and this is called out explicitly in the deployment README rather
  than left implicit.
