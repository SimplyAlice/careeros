# Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Job board ToS violation / account bans from automation | High if full-auto scraping/applying is attempted | High | Human-in-the-loop by default (ADR-0009); prefer official APIs (Adzuna, Greenhouse, Lever) for discovery |
| Target site DOM changes break Playwright selectors | High | Medium (contained by worker isolation) | Portal adapters isolated behind a common interface; failures surface visibly; fixture-based adapter tests in CI |
| CAPTCHA blocks automation entirely | High on some portals | Medium | Detect and surface to the user; never attempt to bypass — a hard ethical/ToS line, not just a technical shortcut |
| LLM hallucinates resume content (fabricated experience) | Medium | High | System prompts constrain the AI to rephrase/emphasize only what's in the master profile; every generated document is human-approved before use |
| Scope creep (project never "ships") | High — this is a large spec | High | Hard milestone boundaries with a defined "done"; explicit non-goals documented; breadth deferred to labeled stretch goals in `portfolio/future-roadmap.md` |
| Azure costs exceed student budget | Medium | Medium | Free-tier/Burstable SKUs during development; documented teardown (`az group delete`) between sessions; reproducible via Bicep |
| Secrets leaked into git history | Medium | High | `.env` gitignored from commit 1; `.env.example` placeholders only; secret-scanning (gitleaks) in CI from Milestone 1 |
| AI provider API costs during heavy testing | Medium | Low–Medium | Cache scoring results; avoid re-scoring unchanged job+profile pairs; use cheaper models for dev-loop testing |
| Solo-developer bus factor / burnout on a large spec | Medium | Medium | Milestone-based delivery means the project has real portfolio value even if paused partway through |

## The Biggest Real Risk

The single greatest risk to this project isn't technical — it's **scope**. The
original spec (10 dashboard pages, 5 notification channels, 6+ job boards, 5+
resume variants, SMS, multi-provider AI from day one) is achievable over
months, but attempting all of it in parallel is how ambitious solo projects
stall at 60% finished across everything instead of 100% finished across a
strong core. The milestone roadmap is the direct mitigation: a working,
deployed, demoable product early (by Milestone 6–7), with additional breadth
layered on afterward.
