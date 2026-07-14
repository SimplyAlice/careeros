# CareerOS — Project Overview

## What It Is

CareerOS is an AI-powered career operations platform: it discovers relevant
job postings from official job-board APIs, scores how well each one matches a
candidate's profile using an LLM, generates tailored resumes and cover
letters, and helps fill out application forms — while keeping a human in
control of every irreversible action.

## Why It Exists

Most "auto-apply" tools either violate job boards' Terms of Service outright
or produce generic, unreviewed application spam. CareerOS is built on the
opposite premise: automation should remove *repetitive* work (re-tailoring a
resume for the fifth time this week, remembering which companies you've
already applied to) while leaving *judgment* — what to say, whether to apply,
when to hit submit — with the person actually job-hunting.

## What It Demonstrates

| Area | Where to look |
|---|---|
| System design & architecture | `architecture/high-level-architecture.md`, `architecture/system-design.md` |
| Cloud-native engineering (Azure) | `architecture/cloud-architecture.md`, `infra/bicep/` |
| Database design | `architecture/database-design.md` |
| AI integration with a provider-agnostic abstraction | `architecture/ai-architecture.md`, `adr/0005-ai-provider-abstraction.md` |
| Responsible automation design | `architecture/browser-automation.md`, `adr/0009-human-in-the-loop-automation.md` |
| Security engineering | `architecture/security.md` |
| Observability & operational excellence | `architecture/observability.md` |
| DevOps / CI/CD | `architecture/deployment-architecture.md`, `.github/workflows/` |
| Architectural decision-making & trade-off analysis | `adr/` (10 decisions, each with alternatives and consequences documented) |

## Project Status

CareerOS is being built incrementally and publicly, milestone by milestone
(see `roadmap/milestones.md`). Each milestone ships working software — this
repository reflects the actual state of development, not a finished mockup.
