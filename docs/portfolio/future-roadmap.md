# Future Roadmap (Post-v1 Stretch Goals)

These are explicitly **out of scope for v1** (see `architecture/system-design.md`
§6 Non-Goals) but documented here so scope discipline reads as a deliberate
choice, not a limitation the project ran out of time for.

## Breadth
- Additional job board integrations: LinkedIn (if/when a compliant API path
  exists), PNet, Careers24, OfferZen, Glassdoor.
- Additional AI provider adapters: OpenAI, Google Gemini (the abstraction in
  ADR-0005 already supports this — it's an adapter, not a redesign).
- Additional notification channels: Slack, Telegram, SMS.
- Additional resume variant templates beyond the initial set (Cloud, Backend,
  Graduate, ATS-optimized).

## AI & Memory
- Semantic/embedding-based memory using pgvector, layered on top of the
  structured-retrieval memory model already in place — richer "similar past
  application" recall than exact-match structured queries alone.
- Interview-preparation assistant: AI-generated likely interview questions
  per role, based on the job description and the user's resume.
- Skills-gap analysis: aggregate scoring rationale across many jobs to
  surface recurring missing skills worth learning.

## Infrastructure
- A parallel Terraform version of the infrastructure, alongside the Bicep
  version (ADR-0010) — specifically to demonstrate both IaC tools, since
  Terraform familiarity is valuable to show separately once the Bicep
  version is solid.
- Multi-region deployment consideration, if/when real usage justifies the
  added complexity and cost (explicitly not justified at current scale — see
  `architecture/cloud-architecture.md` §4).
- A formal security review / lightweight penetration test pass before any
  public-facing use beyond the portfolio demo.

## Product
- A browser extension for one-click "add this job" from any portal.
- A mobile-friendly view of the dashboard (responsive web, not a native app).
- Team/referral features (share application status with a mentor or career
  coach) — would require the RBAC groundwork already in `users.role` to be
  extended into real multi-tenant permission scopes.

## Why These Are Deferred, Not Abandoned

Every item above is achievable within the existing architecture without a
redesign — new job sources and AI providers are new adapters (ADR-0005,
existing `job_sources`/`ai_providers` module pattern), new notification
channels are new adapters in `infrastructure/notifications/`, and RBAC
groundwork already exists in the `users.role` column. Deferring them isn't a
technical limitation — it's the scope discipline documented in
`roadmap/risks.md` as the single biggest risk mitigation for a project this
size.
