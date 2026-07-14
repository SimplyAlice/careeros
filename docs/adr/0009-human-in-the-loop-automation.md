# ADR-0009: Human-in-the-Loop as a Core Design Invariant

## Status
Accepted

## Context
Major job boards (LinkedIn, Indeed, Glassdoor) explicitly prohibit automated
account activity in their Terms of Service, and actively detect/ban automated
sessions. A system that fully auto-applies on a user's behalf, using their
real credentials, risks account suspension and represents a governance/ethics
gap that would be a legitimate concern in a technical interview.

## Decision
Every AI-generated artifact (resume, cover letter, screening answer) and every
automated browser action stops at a human-review or human-confirmation
checkpoint before anything irreversible happens. Full-automatic submission is
an explicit, portal-specific, opt-in setting — off by default — and every
submission records *how* it happened (`applied_via`: manual /
assisted_automation / full_auto) for auditability.

## Alternatives Considered
- **Fully autonomous auto-apply (as originally scoped)** — maximizes
  "hands-off" convenience, but carries real account-ban risk, encourages
  submitting AI-drafted content the user never reviewed (risking factually
  wrong claims reaching a real employer), and is harder to defend as a
  responsible engineering decision in a portfolio review.
- **No automation at all (fully manual)** — safest, but forfeits the
  browser-automation skill demonstration this project is meant to showcase,
  and removes real time-saving value for the user.

## Consequences
- This decision shapes the database schema (`applied_via` tracking,
  `automation_runs.status = paused_for_user` as a normal, expected state, not
  an edge case), the AI prompts (draft-only, human-approved), and the
  automation workflow (see `architecture/browser-automation.md`).
- The system's worst-case automation failure mode is "the user finishes the
  submission manually," not "the system did something unwanted under the
  user's identity" — a meaningfully safer failure mode.
- Full-auto mode remains available for a user who explicitly wants it on a
  specific, ToS-compatible portal, so the capability isn't lost — only the
  default and the audit trail change.
