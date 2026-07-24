# ADR-0012: Profile Management — Single Standalone Profile, Pre-Authentication

## Status
Accepted

## Context

Milestone 4 needed to implement complete profile management: create,
retrieve, update, and validate a job seeker's professional profile
(personal details, skills, experience, education, resume metadata).

This created a direct conflict with existing architecture that had to be
resolved, not silently worked around: Milestone 2 already created
`candidate_profiles`, a table tied to `users` via a required, unique
`user_id` foreign key, with `skills`/`experience`/`education` stored as
JSONB blobs — built in anticipation of the eventual multi-user,
authenticated product. Milestone 4's specification, however, calls for a
single local profile with no user association at all, and normalized
child tables (`skills`, `experience`, `education`, `resume_metadata`)
rather than JSONB. JWT authentication does not exist yet (it's a later
milestone), so there is no `user_id` to attach a profile to even if we
wanted to reuse `candidate_profiles`.

## Decision

Add a new, standalone `profiles` table (plus its normalized child tables)
that is **not** linked to `users`/`candidate_profiles`. Leave
`users`/`candidate_profiles` completely untouched — no migration in this
milestone modifies them.

`profiles` is enforced as a genuine singleton at the database level: a
unique index on the constant expression `(true)`, which is identical for
every row and therefore rejects any insert beyond the first. This is not
just an application-level convention — it holds even under a race
condition, matching the two-layers-of-dedup pattern already established
for job ingestion in Milestone 3 (an app-level pre-check avoids the
common-case round trip; the database constraint is the real guarantee).

### Why a single profile exists

CareerOS's product value (AI job matching, resume tailoring) needs *some*
profile data to operate against, and building that experience end-to-end
is more valuable right now than building multi-user infrastructure that
has no users yet. A single, unauthenticated local profile is the smallest
thing that unblocks every downstream milestone (AI scoring, resume
generation, application tracking) without taking on the real complexity
of accounts, sessions, and per-user data isolation before there's a
concrete reason to need it.

### Why authentication is postponed

Authentication is explicitly a later milestone in the existing roadmap
(`docs/roadmap/milestones.md`) — Milestone 4 does not pull it forward.
Building profile management first, against a single implicit user, lets
the AI/resume/application features that depend on "a profile exists" get
built and demoed sooner, while auth is designed properly on its own
timeline rather than rushed as a prerequisite for unrelated features.

### Future migration path

Once JWT auth and user registration exist, `profiles` needs to become
per-user. The intended path, to be executed as its own milestone (not
speculatively built now):

1. Add a `user_id` column to `profiles`, nullable initially.
2. Backfill: the single existing profile (if any) is assigned to the
   first registered user, or an explicit admin/migration step assigns it.
3. Make `user_id` non-nullable and unique (mirroring `candidate_profiles`'
   current `user_id` uniqueness), and drop the `ix_profiles_singleton`
   constraint — uniqueness moves from "one profile system-wide" to "one
   profile per user."
4. Reconcile with `candidate_profiles`: it's very likely retired at this
   point in favor of the richer, normalized `profiles` schema (now
   finally attached to real users) — a decision to make explicitly at
   that time, not now, since it depends on how the two have each evolved
   in the interim.

This path is deliberately deferred, not designed in detail today —
speculative design for a migration with no immediate driver is a cost
without a matching benefit at this stage.

## Alternatives Considered

- **Extend `candidate_profiles` directly**, adding the new fields/child
  tables to it and requiring a `users` row to exist. Rejected: there is no
  registration flow yet to create that `users` row, so this would require
  inventing an implicit "system user" purely to satisfy a foreign key —
  more complexity than the standalone-table approach, for a multi-user
  capability (the FK relationship) that isn't actually being used yet.
- **Keep the old JSONB `skills`/`experience`/`education` columns on
  `candidate_profiles` and normalize on top of them anyway.** Rejected:
  those columns were never wired to any repository or service code (only
  the schema existed, from Milestone 2) — dropping them in favor of
  `profiles`' normalized tables carries no migration risk to real data,
  and leaves no confusing dual representation for the same concept.
- **Domain entities distinct from ORM models for `Profile` and its
  children**, where `Job`/`Application` (Milestones 2–3) use their ORM
  model directly as the domain model. A deliberate elevation, not a
  blanket rule change: `Profile` carries real, non-trivial business rules
  (duplicate-skill prevention, date/year consistency, salary sanity) that
  deserve a home outside the persistence model; `Job`/`Application`
  didn't have rules complex enough to justify the same separation, and
  remain unchanged.

## Consequences

- `profiles`, `skills`, `experience`, `education`, `resume_metadata` are
  new tables (migration `a9b65b32aeda`); `users`/`candidate_profiles` are
  untouched.
- The codebase now has two different domain-modeling styles side by side
  (ORM-as-domain-model for Job/Application; a distinct domain entity layer
  for Profile) — intentional, and each is explained in its own module's
  docstring so it doesn't read as an inconsistency later.
- `SqlAlchemyProfileRepository` is the only place in the codebase that
  translates between the `Profile` domain entity and its ORM row — the API
  layer and the service layer never see SQLAlchemy models directly.
- Two real Postgres-specific bugs were found and fixed by actually running
  this migration and its tests (not merely writing them): a bare `true` is
  not accepted as an index expression without an extra grouping paren
  (`(true)`), and — a repeat of a Milestone 3 finding — the native
  `remote_preference` enum type isn't dropped by Alembic's autogenerated
  `downgrade()` and needed an explicit `DROP TYPE`.
