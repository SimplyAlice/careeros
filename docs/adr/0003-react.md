# ADR-0003: Use React + TypeScript for the Frontend

## Status
Accepted

## Context
The frontend is an authenticated dashboard (jobs, applications, resumes,
analytics) — not a public, SEO-sensitive marketing site. It needs to be fast
to build, type-safe end-to-end with the backend's typed API, and immediately
recognizable to hiring managers as an industry-standard choice.

## Decision
Use React + TypeScript, built with Vite, client-side rendered.

## Alternatives Considered
- **Next.js** — adds SSR/SSG capability that's genuinely valuable for
  public/SEO-sensitive apps, but this is an authenticated dashboard behind a
  login — SSR provides little benefit here and adds framework complexity
  (server components, routing conventions) that doesn't pay for itself.
- **Vue** — a fine framework, but React has broader industry adoption and is
  the safer signal for a portfolio project aimed at recruiters scanning for
  familiar stacks.

## Consequences
- Vite gives fast local dev iteration (instant HMR) without SSR overhead.
- No server-side rendering means no SEO benefit and no first-paint-before-JS
  — irrelevant for a logged-in dashboard product, so not a real cost here.
- TypeScript across the frontend, paired with FastAPI's typed Pydantic
  schemas, keeps the client/server contract disciplined even without
  generated API clients in v1 (a stretch goal: OpenAPI-generated TS types).
