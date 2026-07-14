# ADR-0008: JWT-Based Authentication (Access + Refresh Tokens)

## Status
Accepted

## Context
The API and frontend are decoupled (SPA + REST API), and authentication needs
to be stateless-friendly for horizontal scaling of the API tier, while still
allowing token revocation (logout, password change) — a pure stateless JWT
scheme can't revoke a token before its natural expiry.

## Decision
Use short-lived JWT access tokens (~15 min) plus longer-lived refresh tokens,
stored hashed server-side with a revocation list. Refresh tokens are
delivered via an httpOnly, Secure, SameSite=Strict cookie; access tokens are
sent as a bearer token in the `Authorization` header.

## Alternatives Considered
- **Server-side session cookies** — simpler CSRF story in some respects, and
  trivially revocable, but requires a shared session store for horizontal
  scaling (defeating some of the statelessness benefit) and is a less natural
  fit for a decoupled SPA/API architecture than token-based auth.
- **Pure stateless JWT with no revocation mechanism** — simplest to
  implement, but cannot support logout-everywhere or forced invalidation on
  password change/compromise — an unacceptable security gap for a system
  storing career/PII data.

## Consequences
- Requires a `refresh_tokens` (or equivalent revocation-list) table and a
  `/auth/refresh` endpoint — more moving parts than a stateless-only scheme.
- Gains real revocation capability: a compromised refresh token or a
  password change can invalidate all outstanding sessions immediately.
- The API tier remains horizontally scalable (any instance can validate an
  access token's signature without a shared session store); only the
  revocation-list lookup touches the database, and only on refresh, not on
  every request.
