# Lessons Learned

This is a **living document**, updated at the end of each milestone as the
project is actually built — it intentionally starts empty of implementation
lessons, since none have been learned yet at Milestone 0. Populating it
honestly (including what didn't work, what got redesigned, and why) is part
of what makes it credible to a reader; a lessons-learned page written entirely
in hindsight after the project is "done" is less convincing than one that
visibly accumulates over time.

## Format (per milestone, once implementation begins)

```
### Milestone N — <name>

**What went as planned:**
-

**What didn't, and why:**
-

**What I'd do differently next time:**
-

**A concept I understood better after building this than after just reading about it:**
-
```

## Milestone 0 — Foundations

**What went as planned:** the docs-first approach surfaced the automation
ToS/ethics issue *before* any code was written, which is exactly the value a
design phase is supposed to provide — catching a costly redesign early instead
of after building a fully autonomous automation pipeline.

**What I'd flag for early revisit:** the AI provider abstraction (ADR-0005)
and the Celery/Redis choice (ADR-0004) are the two decisions most likely to
need revisiting once real usage patterns emerge — both are called out
explicitly in their ADRs as decisions made with reasonable assumptions, not
certainties.
