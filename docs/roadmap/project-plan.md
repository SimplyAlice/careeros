# Project Plan — Process & Workflow

## Git Workflow

- `main` — always deployable.
- `milestone/N-short-name` — one branch per milestone, merged into `main` via PR.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `test:`) from
  the start — a small, free signal of engineering maturity on a portfolio
  repo, and it makes `roadmap/milestones.md` traceable directly against git
  history.

## Milestone Process

Every milestone follows the same cycle, mirroring how a real engineering team
would work:

1. **Plan** — objective, affected files/folders, any schema change, restated
   here before code is written.
2. **Build** — incremental commits, not one giant diff.
3. **Test** — unit tests for new logic, integration tests where a real
   dependency (DB, Redis) is involved.
4. **Document** — update relevant `docs/architecture/*.md` if the milestone
   changes a documented decision; update the README if user-facing behavior
   changed.
5. **Review** — a definition-of-done checklist is presented; the milestone
   isn't considered complete until it's confirmed working.
6. **Commit & tag** — meaningful commit messages; milestone completion tagged
   in git for traceability.

## Definition of Done (applies to every milestone unless a milestone doc says otherwise)

- [ ] Code runs locally via `docker-compose up` without manual workarounds.
- [ ] New functionality has test coverage (unit, and integration where a real
      dependency is involved).
- [ ] Linting and type-checking pass locally and in CI.
- [ ] Relevant docs updated (architecture doc, ADR if a new decision was made,
      README if user-facing).
- [ ] No secrets committed (verified by CI secret-scanning from Milestone 1
      onward).
- [ ] The milestone's specific "what does 'done' mean" criteria (stated at
      milestone kickoff) are met.

## Decision Log Process

Any architecturally significant decision made during implementation (not
already covered by an existing ADR) gets a new ADR before the related code is
merged — not written retroactively from memory after the fact. This keeps the
`docs/adr/` folder an accurate record of *why*, not just a post-hoc
rationalization exercise.
