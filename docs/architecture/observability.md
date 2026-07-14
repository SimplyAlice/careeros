# Observability

## 1. Philosophy

Observability here is built to answer two different questions, and the design
distinguishes between them deliberately:

1. **"Is the system healthy?"** — infrastructure-level: uptime, latency,
   error rate, resource usage.
2. **"Is the product doing what it's supposed to?"** — business-level: is
   ingestion actually finding jobs, is scoring actually running, is the
   Greenhouse adapter's failure rate creeping up.

A system can be "healthy" by the first definition (200 OK everywhere) while
being broken by the second (automation silently failing on every attempt).
Both are tracked, not just the first — this is the difference between
surface-level monitoring and real operational maturity, and it's a
deliberate talking point for interviews.

## 2. Structured Logging

- `structlog` producing JSON output across API and worker processes.
- Consistent field set on every log line: `request_id`, `user_id` (when
  authenticated), `task_name` (for worker logs), `timestamp`, `level`.
- `request_id` is generated at the API edge and threaded through to any
  Celery task enqueued as part of that request, so a single user action can be
  traced end-to-end across process boundaries in Application Insights.
- No secrets, tokens, or full request bodies containing PII are ever logged —
  logging middleware explicitly redacts known-sensitive fields.

## 3. Health Endpoints

| Endpoint | Checks | Used by |
|---|---|---|
| `/health` | Process is up, can respond | Azure App Service liveness probe |
| `/health/ready` | DB connection succeeds, Redis connection succeeds | Readiness gating during deploys — a new instance isn't sent traffic until this passes |

## 4. Metrics

**Infrastructure metrics** (via Application Insights auto-instrumentation):
request rate, latency percentiles, error rate, CPU/memory per instance.

**Business metrics** (custom, emitted explicitly from application code):

| Metric | Why it matters |
|---|---|
| Jobs ingested / hour, by source | Detects a silent ingestion failure (e.g. Adzuna API key expired) before a user notices "no new jobs" |
| Applications submitted / day | The core product usage signal |
| Automation success/failure rate, by portal | Surfaces exactly which portal adapter is degrading — the earliest signal of a DOM change breaking a selector |
| AI call latency and approximate token cost, by use case | Ties directly to both performance and the cost-control requirement |
| Score distribution (are most jobs scoring very high/low) | A sanity check on the scoring prompt itself — a bug that scores everything 95 is a silent product defect, not a crash |

## 5. Tracing

Application Insights SDK auto-instruments FastAPI request handling and
outbound calls (Postgres, Redis, HTTP calls to LLM providers and job-source
APIs). A slow end-to-end request is traceable to its actual bottleneck (e.g.
"the Anthropic completion call took 4.2s of a 4.5s total") rather than left as
an undifferentiated "the API is slow."

## 6. Alerting

| Condition | Alert |
|---|---|
| API error rate > threshold over 5 min | Page/notify — likely a code or dependency regression |
| `/health/ready` failing repeatedly | Page/notify — DB or Redis connectivity issue |
| Automation failure rate for a given portal spikes | Notify — likely a DOM/selector break, actionable and specific |
| AI call latency p95 exceeds threshold | Notify — provider degradation or a runaway prompt |

Alerts are written to be **actionable and specific** ("Greenhouse automation
failure rate exceeded 50% in the last hour") rather than generic ("something
is wrong") — a generic alert trains people to ignore alerts, which defeats the
purpose of having them.

## 7. Audit Trail vs. Operational Logs

Two logically distinct log stores exist, intentionally:

- **`audit_logs`** — security-relevant events (login, password change,
  settings change, data export/delete). Append-only, access-restricted, kept
  for compliance/accountability purposes.
- **`automation_logs` / application logs** — operational events (job found,
  automation step succeeded/failed). Used for debugging and product
  analytics, not security review.

Conflating these is a common real-world mistake (either audit logs get lost in
noisy operational logs, or operational debugging is hampered by
over-restricted access to audit-grade logs) — CareerOS separates them from
the start.
