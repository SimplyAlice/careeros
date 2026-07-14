# ADR-0007: Use Microsoft Azure as the Cloud Provider

## Status
Accepted

## Context
The project must be deployed to a real cloud environment to demonstrate cloud
engineering skill, and the author's explicit career direction (Cloud Support
Engineer → Cloud Engineer) points at Azure specifically.

## Decision
Deploy to Microsoft Azure: App Service (API), Container Apps (workers), Azure
Database for PostgreSQL, Azure Cache for Redis, Blob Storage, Key Vault, and
Application Insights/Azure Monitor for observability.

## Alternatives Considered
- **AWS** — equally valid technically (ECS/App Runner, RDS, ElastiCache, S3,
  Secrets Manager, CloudWatch are direct analogues), and arguably has broader
  market share. Not chosen because the explicit goal is Azure-specific skill
  depth for a defined career path, not cloud-provider-agnostic breadth.
- **GCP** — same reasoning as AWS; a fine platform, not the target one here.

## Consequences
- Deep, demonstrable familiarity with a coherent set of Azure managed
  services (App Service, ACR, Managed Postgres, Key Vault, Monitor) that maps
  directly onto interview conversations for Azure-aligned roles.
- Some Azure-specific concepts (App Service deployment slots, Key
  Vault-via-managed-identity, Container Apps' KEDA-based scaling) don't
  transfer 1:1 to AWS/GCP — an accepted trade given the explicit goal is
  Azure depth, not multi-cloud portability.
- IaC is written in Bicep (Azure-native) rather than Terraform — see
  `adr/0010-bicep-iac.md` for that sub-decision specifically.
