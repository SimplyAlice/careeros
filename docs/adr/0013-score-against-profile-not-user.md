# ADR-0013: Score Jobs Against the Profile, Not a User

## Status
Accepted

## Context

Milestone 5 implements AI job scoring: comparing a candidate's profile
against a job posting and persisting the result. The `job_matches` table
already existed (Milestone 2), with a required, non-nullable `user_id`
foreign key to `users`.

This created the same class of conflict Milestone 4 resolved for
`candidate_profiles`: there is still no registration/authentication flow,
so no real `users` row can exist. `job_matches.user_id` being `NOT NULL`
meant the table, as originally designed, could not accept a single insert
in the system's current pre-auth state — a real blocker, not a stylistic
concern, discovered while implementing the scoring service.

Meanwhile, Milestone 4 introduced `profiles` — the actual single local
profile the product operates against right now. Scoring needs to compare
*that* profile to a job, not a `user` that doesn't exist yet.

## Decision

Alter `job_matches` (migration `980eb04284d4`):

1. Add `profile_id` (FK to `profiles.id`, nullable — see "Why nullable"
   below) — the column Milestone 5's scoring service actually populates.
2. Make `user_id` nullable (previously `NOT NULL`) — kept, not dropped,
   so it's ready to become the real per-user reference once
   authentication exists, without reintroducing the column later.
3. Add `matched_skills`/`missing_skills` as JSONB string-array columns —
   the AI scoring response is structured (score, rationale, matched
   skills, missing skills; see `docs/architecture/ai-architecture.md`),
   and folding the skill lists into the existing free-text `reasoning`
   column would make them unusable for a frontend to render as distinct
   chips/tags without re-parsing text. `CandidateProfile.skills`
   (Milestone 2) already established JSONB string arrays as this
   codebase's answer for exactly this kind of data.

### Why nullable, not `NOT NULL`

Unlike `profiles.email` or `jobs.title`, there's no possible "first row"
problem to solve for `profile_id` — every match ever created *does* have
a real profile. `profile_id` is nullable purely because Alembic can't
safely add a `NOT NULL` column to a table that might already contain rows
without a backfill step, and no backfill is warranted for a column with
zero real historical data (mirrors the reasoning already used for
`profiles.email`-adjacent decisions in `docs/adr/0012-profile-management.md`).
The scoring service (`JobScoringService.score_job`) always populates it;
the looser DB constraint is a migration-safety choice, not a business
rule relaxation.

## Alternatives Considered

- **Create a "system user" row to satisfy the existing `user_id NOT
  NULL` constraint**, leaving the schema untouched. Rejected for the
  same reason ADR-0012 rejected the equivalent move for profiles: it
  invents multi-user machinery (a real row in a table meant to represent
  actual accounts) purely to route around a constraint, for a capability
  (real per-user attribution) that doesn't exist yet and would need to be
  redone correctly once auth lands anyway.
- **Fold `matched_skills`/`missing_skills` into the existing `reasoning`
  text column** as appended sentences ("Matched skills: Python, Azure.").
  Rejected: it works, but produces a lossy, re-parse-required
  representation for data that's naturally structured and cheap to store
  properly — and JSONB string-array columns already have precedent in
  this schema.
- **Add a `MatchResult` entity to the domain layer distinct from
  `JobMatch`'s ORM model**, mirroring `Profile`'s treatment in Milestone
  4. Considered and partially adopted: `MatchResult`
  (`app/domain/value_objects/match_result.py`) *is* a real domain value
  object — it's what `LLMProvider`'s raw response gets validated into
  before persistence — but `JobMatch` itself remains ORM-direct, like
  `Job`/`Application`. A match doesn't carry business rules complex
  enough (beyond the score range, already enforced at the database level
  since Milestone 2) to justify a full parallel domain entity the way
  `Profile`'s validation rules did.

## Consequences

- `job_matches.user_id` is now nullable across the whole codebase — any
  future code that assumes it's always populated (e.g. an analytics query
  grouping by user) needs to account for that until auth lands and new
  rows start populating it for real.
- `JobRepository` (Milestone 3) gained a `get_by_id` method — a minimal,
  additive port extension needed so the scoring service can load one
  specific job. Not a redesign of the jobs subsystem.
- The future reconciliation path is now the same shape for both
  `profiles` and `job_matches`: once auth exists, both gain real,
  populated `user_id`/attribution, and the temporary nullability this ADR
  introduces is tightened back to `NOT NULL` in a follow-up migration —
  planned together with the `profiles` reconciliation already described
  in `docs/adr/0012-profile-management.md`, not designed in detail now.
