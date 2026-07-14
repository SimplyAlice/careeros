# ADR-0010: Use Bicep for Infrastructure as Code

## Status
Accepted

## Context
All Azure infrastructure (App Service, Container Apps, Postgres, Redis, Blob
Storage, Key Vault) needs to be reproducible from code — for disaster
recovery, environment parity (dev/staging/prod), and to avoid undocumented
manual portal configuration.

## Decision
Use Bicep, organized as one module per Azure resource under `infra/bicep/`,
parameterized per environment.

## Alternatives Considered
- **Terraform** — more portable across cloud providers and more broadly
  recognized as an industry-standard IaC skill (arguably a stronger resume
  line for some roles), but requires managing state files (remote state
  backend, locking) that add operational overhead for a solo project, and its
  Azure resource coverage lags slightly behind Azure's own first-party Bicep
  support for newer services.
- **ARM JSON templates directly** — Bicep's predecessor; strictly more
  verbose and harder to read/maintain than Bicep for equivalent
  functionality, with no upside once Bicep is available.

## Consequences
- No state file to manage or lose — Bicep resolves current state directly
  against Azure at deploy time, removing an entire class of "state drift"
  problems a solo developer would otherwise need to manage carefully.
- `az deployment ... --what-if` gives a preview of changes before applying,
  supporting safe, reviewable infrastructure changes.
- Bicep is Azure-only — acceptable given ADR-0007 already commits to Azure as
  the sole target platform. A Terraform version is documented as a legitimate
  future stretch goal (`portfolio/future-roadmap.md`) specifically because
  Terraform familiarity is valuable to demonstrate separately, once the Bicep
  version is solid.
