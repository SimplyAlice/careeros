# ADR-0006: Use Playwright for Browser Automation

## Status
Accepted

## Context
Assisted application requires navigating job portals, filling forms, and
uploading documents in a browser context, handling dynamic single-page-app
style forms reliably, and failing predictably (not silently) when a portal
changes or blocks automation.

## Decision
Use Playwright (Python) for all browser automation, with a per-portal adapter
implementing a common `PortalAutomation` interface.

## Alternatives Considered
- **Selenium** — the long-standing standard, but its explicit-wait model is
  more manual and flakier against modern dynamic SPA-style forms than
  Playwright's built-in auto-waiting, which increases false-failure rates in
  exactly the scenario (form filling on modern portals) this project targets.
- **Browser Use / Stagehand** (LLM-driven browser agents) — appealing for
  their ability to adapt to UI changes without hand-written selectors, but
  less mature/production-proven, harder to debug deterministically when
  something goes wrong (the failure mode is "the LLM made an unexpected
  decision" rather than "this selector wasn't found"), and less controllable
  for the human-confirm gate this project's design depends on. Playwright's
  determinism is a better fit for a workflow that must reliably pause at a
  precise point (before final submit) every time.

## Consequences
- Selector maintenance is a real, ongoing cost — job portals change their
  DOM, and adapters will need updates. Mitigated architecturally: each portal
  adapter is isolated, small, and covered by fixture-based tests, so a
  breakage is a contained, diagnosable fix rather than a system-wide outage
  (see `architecture/browser-automation.md` §4).
- Determinism and debuggability are prioritized over adaptability — a
  reasonable trade given the human-in-the-loop design invariant: the system
  doesn't need to gracefully improvise around a broken form, it needs to fail
  visibly and hand control back to the user.
