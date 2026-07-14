# System Design — Product Vision & Requirements

## 1. What CareerOS Is

CareerOS is an AI-powered career operations platform. It helps a job seeker
discover relevant roles, understand how well they match those roles, tailor
application materials, prepare for interviews, and track the entire job search
— while keeping a human in control of every irreversible action (submitting an
application).

## 2. Why It's Designed This Way (not a stealth auto-apply bot)

LinkedIn, Indeed, and Glassdoor prohibit automated account activity in their
Terms of Service. A system that silently submits applications under a real
user's identity is fragile — it risks account bans — and it's a weaker
engineering story than one that demonstrates judgment about automation risk.
CareerOS's core design constraint is therefore:

> **Every AI-generated artifact and every automated action stops at a human
> checkpoint before anything irreversible happens, unless the user explicitly
> opts into full automation for a specific, ToS-compatible portal.**

This single constraint shapes the database schema (`applied_via` tracking),
the automation architecture (pause-before-submit), and the AI prompts (never
fabricate facts, always present for approval). It's referenced throughout this
docs set rather than restated — treat it as a standing design invariant.

## 3. Target User

A software engineering student/new grad applying to a moderate volume of
roles per week, who wants less time spent manually re-tailoring resumes, a
single source of truth for application status, objective fit signal per
posting, and structured help with recurring screening questions.

## 4. Functional Requirements

### Job Discovery
- **FR-1**: Ingest job postings from official APIs (Adzuna, Greenhouse, Lever) on a schedule.
- **FR-2**: Deduplicate postings across sources (company + title + location within a time window).
- **FR-3**: Allow manual addition of a job via URL/description paste.

### AI Matching
- **FR-4**: Compute a 0–100 compatibility score between a job description and the user's active profile.
- **FR-5**: Explain the score in natural language (matched skills, gaps, risk factors).
- **FR-6**: Generate that explanation through a swappable LLM provider behind a common interface.

### Resume Engine
- **FR-7**: Store a canonical "master profile" (structured: experience, skills, education, projects).
- **FR-8**: Generate tailored resume variants per job/track from the master profile.
- **FR-9**: Version every generated resume; all versions retrievable later.
- **FR-10**: Render resumes to ATS-safe PDF (single column, standard headings, no tables/graphics in body).

### Cover Letter Engine
- **FR-11**: Generate a cover letter referencing the specific role, company, and 2–3 concrete points of fit, grounded in the actual job description and profile.

### Application Tracking
- **FR-12**: Log an application (job, resume version, cover letter version, date, status).
- **FR-13**: Track status transitions: Saved → Applied → Screening → Interview → Offer/Rejected.
- **FR-14**: Prevent duplicate applications to the same job posting (enforced at the DB level, not just in application code).

### Assisted Application (Browser Automation)
- **FR-15**: For supported portals, open the application form and pre-fill known fields via Playwright.
- **FR-16**: Pause before final submission by default; full-auto submit is opt-in, off by default, and distinctly logged.
- **FR-17**: Detect and surface (never attempt to solve) CAPTCHAs, unexpected page states, and session expiry.

### Memory
- **FR-18**: Retain structured history of past applications, resumes, recruiter contacts, and outcomes; use it to avoid duplicate work and inform future scoring/tailoring.

### Notifications
- **FR-19**: Notify via email and Discord for: new high-match jobs, application submitted, interview logged, follow-up due.

### Dashboard & Analytics
- **FR-20**: Show applications submitted, response rate, interview rate, and trend over time.

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Security | Passwords hashed (bcrypt/argon2), JWT auth, no secrets in source control, RBAC groundwork for future multi-tenant use |
| Reliability | Background jobs (scraping, AI calls) retryable and idempotent |
| Observability | Every service exposes a health endpoint; structured JSON logs; key business events emitted as metrics |
| Performance | API p95 latency < 300ms for CRUD endpoints (AI/automation endpoints are async and exempt) |
| Portability | Identical container image runs locally (Docker Compose) and in Azure App Service |
| Maintainability | Typed Python (mypy) and TypeScript enforced in CI; no unjustified `Any` across module boundaries |
| Cost | Cloud footprint fits within Azure free-tier/student credits during development |
| Compliance | No automated action may violate a target platform's Terms of Service |

## 6. Explicit Non-Goals (v1)

- No browser extension.
- Depth on 2–3 job sources beats shallow support for 10 — broader board coverage is a post-v1 stretch goal.
- No mobile app.
- No SMS notifications in v1 (documented as optional/future).

These are deliberate scope cuts, not omissions — see `roadmap/risks.md` for why
scope discipline is treated as the single biggest risk to this project.
