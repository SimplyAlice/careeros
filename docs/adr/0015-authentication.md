# ADR-0015: Milestone 7 Is Authentication (JWT), Not the React Dashboard

## Status
Accepted

## Context

`docs/roadmap/milestones.md` originally scheduled Milestone 7 as "React
dashboard v1" (auth flow + several frontend pages, wired to the real
API). The instructions for this milestone, however, are exclusively
backend-oriented — Clean Architecture layers, repository interfaces,
infrastructure adapters, Alembic migrations, DTOs — with no frontend
scaffolding anywhere in the repository to build against. Building a React
application under those instructions would be a scope mismatch, not a
faithful implementation of what was actually asked for.

Separately, JWT authentication has been referenced as pending,
overdue work since Milestone 0: `docs/adr/0008-jwt-auth.md` designed the
access/refresh token scheme before any of it existed; `docs/adr/0012-profile-management.md`
and `docs/adr/0013-score-against-profile-not-user.md` both explicitly
deferred reconciling `profiles`/`job_matches` with real users to "once
auth lands." Nothing in the roadmap actually delivered it yet.

## Decision

Implement JWT authentication as Milestone 7: registration, login, token
refresh (with rotation), logout (revocation), and a protected
`GET /auth/me` endpoint demonstrating the `get_current_user` dependency
future milestones will reuse. The React dashboard moves to Milestone 8.
This mirrors exactly how Profile Management was inserted ahead of AI
Scoring back in Milestone 4 — a documented renumbering, not a silent
scope change.

### Scope boundary: authentication is additive, not a retrofit

This milestone deliberately does **not** attach `profiles`, `jobs`,
`matches`, or generated documents to real users, despite now having real
users to attach them to. That reconciliation was always described as its
own future step (see the "future migration path" sections of ADR-0012
and ADR-0013), and folding it into this milestone would mean rewriting
every existing repository, service, and endpoint's authorization model in
the same change that introduces authentication itself — exactly the kind
of scope-creep `docs/roadmap/risks.md` already names as this project's
single biggest risk. Milestone 7 delivers a complete, correctly-designed
authentication system as a standalone capability; wiring the rest of the
product to require and scope by it is the next, separately-scoped
milestone.

### Refresh tokens are opaque, not JWTs

Access tokens are signed JWTs (stateless, no DB lookup per request,
15-minute default lifetime). Refresh tokens are cryptographically random
opaque strings (`secrets.token_urlsafe(32)`), not JWTs — only their
SHA-256 hash is ever persisted, in a new `refresh_tokens` table with
`revoked_at`/`expires_at` columns, giving real revocation (logout,
rotation-on-refresh) that a self-contained JWT can't provide without
defeating its own statelessness. This is the concrete implementation of
the scheme `docs/adr/0008-jwt-auth.md` designed at Milestone 0.

Refresh tokens are hashed with SHA-256, not bcrypt — bcrypt's deliberate
slowness exists to resist brute-forcing low-entropy human-chosen
passwords; a 32-byte random token has no such guessable structure, so
bcrypt would only add latency without a corresponding security benefit.

### Refresh token rotation

Every successful `/auth/refresh` call revokes the presented refresh token
and issues a new one. A stolen refresh token is single-use from the
attacker's perspective the moment the legitimate client refreshes again —
a standard mitigation for refresh-token theft.

## Alternatives Considered

- **Skip authentication and build the React dashboard against the
  unauthenticated `profile`/`jobs`/`matches` endpoints as they exist
  today.** Rejected outright given this milestone's explicit,
  backend-only instructions — but also a poor sequencing choice on its
  own merits: the dashboard would need to be substantially reworked the
  moment real auth lands, rather than being built against a stable,
  already-authenticated API.
- **Reconcile `profiles`/`job_matches`/generated documents with real
  users in this same milestone.** Rejected for the scope-discipline
  reason above — this is real, necessary work, but it deserves its own
  milestone with its own test coverage and its own review, not to be
  bundled invisibly into "add login."
- **JWT refresh tokens instead of opaque random strings.** Rejected: a
  self-contained JWT refresh token either can't be revoked before its
  natural expiry (defeating the point of a revocation list) or requires
  storing/checking a hash of it anyway — at which point an opaque random
  token is simpler and carries no unnecessary claims/signature overhead.
- **`passlib` instead of `bcrypt` directly.** Rejected: `passlib` wraps
  bcrypt (among other algorithms) behind an abstraction this project
  doesn't need — one settled hashing algorithm, called directly, is
  simpler and has one fewer dependency to reason about.

## Consequences

- `users` (Milestone 2) gains `password_hash` (NOT NULL — safe as a
  direct add, since no registration flow existed before this milestone
  and the table had no real rows) and a new `refresh_tokens`
  relationship.
- A new `refresh_tokens` table, following the same
  `CreatedAtMixin`-only, point-in-time-record shape used by `JobMatch`,
  `GeneratedResume`, and `GeneratedCoverLetter`.
- `GET /auth/me` is the first genuinely protected endpoint in the
  codebase. Every other endpoint (`profile`, `jobs`, `matches`, `resumes`,
  `cover-letters`) remains unauthenticated, by design, until the
  reconciliation milestone described above.
- `requirements.txt` gains `bcrypt` and `pyjwt`; both ship their own type
  stubs, so no mypy override was needed (unlike `fpdf2` in Milestone 6).
